import asyncio
import functools
import json
import os
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import uuid
import httpx
from urllib.parse import unquote, urlparse, parse_qs
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tempfile

from dotenv import load_dotenv
from groq import Groq
from firebase_admin import firestore
from firebase_config import get_db, firebase_admin
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from google import genai
from google.genai import types

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
# USERS_FILE removed in favor of Firestore
# HISTORY_DIR removed in favor of Firestore
UPLOADS_DIR = Path("static/uploads")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="YouTube Transcripter",
    description="AI-powered notes generator from YouTube videos",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
db = get_db()

def send_inactivity_email(to_email: str):
    """Send an email to inactive users."""
    subject = "We Miss You! Come Back to YouTube Transcripter"
    body = """
    <html>
    <body>
        <h2>Hello! 👋</h2>
        <p>We noticed you haven't logged in for over 24 hours.</p>
        <p>We have new features waiting for you! Come back and explore our latest updates.</p>
        <p><a href="http://localhost:8000/login" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Login Now</a></p>
        <p>Best regards,<br>The YouTube Transcripter Team</p>
    </body>
    </html>
    """

    try:
        if "your-email" in SMTP_EMAIL:
            print(f"📧 [MOCK EMAIL] To: {to_email} | Subject: {subject}")
            return

        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")

def hash_password(password: str) -> str:
    """Hash password with SHA-256 + random salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    salt, hashed = stored_hash.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed

# CORS middleware is configured above with the app declaration

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class GenerateRequest(BaseModel):
    youtube_url: str
    output_language: str = "English"
    model: str = "gemini"  # "gemini" or "qwen"

class ProfileUpdateRequest(BaseModel):
    name: str = ""
    dob: str = ""
    gender: str = ""
    role: str = "student"
    photo_url: str = ""


# ═══════ Database Helpers (Firestore) ═══════

def get_user(email: str) -> dict:
    """Get user document from Firestore."""
    if not db:
        return {}
    doc_ref = db.collection("users").document(email)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_user(email: str, data: dict):
    """Save user document to Firestore."""
    if not db:
        return
    db.collection("users").document(email).set(data, merge=True)

def get_user_history(email: str) -> list:
    """Get history sub-collection for a user."""
    if not db:
        return []
    history_ref = db.collection("users").document(email).collection("history")
    docs = history_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [d.to_dict() for d in docs]

def save_history_item(email: str, item: dict):
    """Save history item to sub-collection."""
    if not db:
        print("❌ DB is None in save_history_item")
        return
    print(f"💾 Saving history for {email}: {item['id']}")
    try:
        db.collection("users").document(email).collection("history").document(item["id"]).set(item)
        print("✅ History saved successfully")
    except Exception as e:
        print(f"❌ Failed to save history: {e}")

def delete_history_item_db(email: str, note_id: str):
    """Delete history item from sub-collection."""
    if not db:
        return
    db.collection("users").document(email).collection("history").document(note_id).delete()

def update_task_status(task_id: str, status: str, result: dict = None, error: str = None):
    """Update task status in Firestore."""
    if not db:
        return
    data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
    if result:
        data["result"] = result
    if error:
        data["error"] = error
    db.collection("tasks").document(task_id).set(data, merge=True)

# ═══════ Transcript Chunking Helpers ═══════

# Thresholds (in characters)
SHORT_THRESHOLD = 12000    # < 12K chars ≈ < 15 min video
LONG_THRESHOLD = 50000     # > 50K chars ≈ > 60 min video
CHUNK_SIZE = 10000         # ~10K chars per chunk ≈ ~2500 tokens
CHUNK_OVERLAP = 500        # 500 char overlap to avoid cutting mid-sentence

def chunk_transcript(transcript: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Split a long transcript into overlapping chunks, breaking at sentence boundaries."""
    if len(transcript) <= chunk_size:
        return [transcript]
    
    chunks = []
    start = 0
    while start < len(transcript):
        end = start + chunk_size
        
        if end < len(transcript):
            # Try to break at a sentence boundary (., !, ?)
            boundary = transcript.rfind('. ', start + chunk_size - 1000, end)
            if boundary == -1:
                boundary = transcript.rfind('? ', start + chunk_size - 1000, end)
            if boundary == -1:
                boundary = transcript.rfind('! ', start + chunk_size - 1000, end)
            if boundary != -1:
                end = boundary + 1  # Include the punctuation
        
        chunk = transcript[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap  # Overlap to avoid losing context
        if start >= len(transcript):
            break
    
    return chunks

# Prompt for chunked medium-length videos (15-60 min)
CHUNK_SUMMARY_PROMPT = """You are an expert note-taker. This is PART {chunk_num} of {total_chunks} from a video transcript.

Generate detailed notes for THIS SECTION in **{language}**. Focus on the MOST IMPORTANT points discussed.

📋 FORMAT:
### Section {chunk_num} Key Points
- 📝 **Point:** [Explanation with detail]
- 💡 **Example:** [Real-world example]
(Continue for each major point in this section)

**RULES:**
1. All text in **{language}**
2. Be detailed but focus on what matters most
3. Use emojis for visual engagement
4. Include practical examples

TRANSCRIPT SECTION:
{transcript}
"""

# Prompt for long videos (> 1 hour) — key points only
KEY_POINTS_PROMPT = """You are an expert note-taker. This is PART {chunk_num} of {total_chunks} from a LONG video transcript (over 1 hour).

Extract ONLY the most critical and important points from THIS SECTION in **{language}**.
Skip filler, repetition, and minor details. Focus on KEY TAKEAWAYS only.

📋 FORMAT:
### Section {chunk_num} — Critical Points
- 🔑 **[Key Point Title]:** [Concise but clear explanation]
(List only 3-5 most important points from this section)

**RULES:**
1. All text in **{language}**
2. ONLY the most important, must-know points
3. Be concise — no filler
4. Skip repeated content

TRANSCRIPT SECTION:
{transcript}
"""

# Merge prompt to combine chunk notes into final document
MERGE_PROMPT = """You are an expert note organizer. Below are notes generated from MULTIPLE SECTIONS of a single YouTube video.
Your job: Merge them into ONE cohesive, well-structured document in **{language}**.

📋 **FORMAT YOUR MERGED NOTES EXACTLY LIKE THIS:**

# 📺 Video Notes

## 🎯 Main Topic
[Identify the overall subject from all sections]

## 📌 Key Points

### 1️⃣ [First Major Point]
- 📝 **Explanation:** [Detailed explanation in {language}]
- 💡 **Real-time Example:** [Practical example in {language}]
- 🔑 **Key Takeaway:** [One-line summary]

[Continue numbering ALL major points across sections...]

## 🧠 Important Concepts Explained
| Concept | Definition | Example |
|---------|-----------|---------|
| [Term] | [Definition] | [Example] |

## ⚡ Quick Summary
- ✅ [Key takeaway 1]
- ✅ [Key takeaway 2]
- ✅ [Key takeaway 3]

## 🎓 Conclusion
[Overall message and key learnings]

**RULES:**
1. ALL output in **{language}**
2. Remove duplicate points across sections
3. Maintain logical flow and ordering
4. Keep the most important details, skip repetition
5. Use emojis for visual engagement 🎨
6. Number all points for easy reference

SECTION NOTES TO MERGE:
{chunk_notes}
"""

async def generate_for_model(prompt: str, model: str, language: str, role_modifier: str) -> str:
    """Route generation to the selected model (Gemini or Qwen/Groq)."""
    if model == "qwen":
        return await generate_notes_with_qwen3_raw(prompt, language, role_modifier)
    else:
        # Gemini with Qwen fallback
        notes = await generate_notes_with_gemini_raw(prompt, language, role_modifier)
        if not notes:
            print("⚠️ Gemini failed, falling back to Qwen...")
            notes = await generate_notes_with_qwen3_raw(prompt, language, role_modifier)
        return notes

async def generate_notes_with_gemini_raw(prompt: str, language: str = "English", role_modifier: str = "") -> str:
    """Generate notes using Gemini with a pre-built prompt (no template replacement)."""
    retries = 3
    base_delay = 2
    loop = asyncio.get_running_loop()
    
    full_prompt = prompt
    if role_modifier:
        full_prompt = full_prompt + role_modifier

    for attempt in range(retries):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = await loop.run_in_executor(
                None,
                functools.partial(
                    client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=8192,
                    )
                )
            )
            if response.text:
                return response.text
            return None
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"⚠️ Gemini 429. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
            print(f"⚠️ Gemini raw prompt failed: {e}")
            return None
    return None

async def generate_notes_with_qwen3_raw(prompt: str, language: str = "English", role_modifier: str = "") -> str:
    """Generate notes using Groq with a pre-built prompt (no template replacement)."""
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not set, skipping Qwen")
        return None
    
    try:
        full_prompt = prompt
        if role_modifier:
            full_prompt = full_prompt + role_modifier
        
        client = Groq(api_key=GROQ_API_KEY)
        models_to_try = [
            "qwen/qwen3-32b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "mixtral-8x7b-32768",
        ]
        messages = [
            {"role": "system", "content": "You are an expert educational note-taker."},
            {"role": "user", "content": full_prompt}
        ]
        
        loop = asyncio.get_running_loop()
        for model_id in models_to_try:
            try:
                print(f"🤖 Trying Groq model: {model_id}")
                response = await loop.run_in_executor(
                    None,
                    functools.partial(
                        client.chat.completions.create,
                        model=model_id,
                        messages=messages,
                        max_tokens=8192,
                        temperature=0.7,
                    )
                )
                if response.choices and response.choices[0].message.content:
                    print(f"✅ Generated with Groq/{model_id}")
                    return response.choices[0].message.content
            except Exception as model_err:
                print(f"⚠️ Groq model {model_id} failed: {model_err}")
                continue
        return None
    except Exception as e:
        print(f"⚠️ Groq raw prompt failed entirely: {e}")
        return None


async def process_note_generation(task_id: str, req: GenerateRequest, user_email: str, user_role: str):
    """Background task to generate notes — supports any video length."""
    try:
        # Step 1: Extract video ID
        update_task_status(task_id, "processing", {"step": "extracting_video_id"})
        video_id = extract_video_id(req.youtube_url)

        # Step 2: Fetch transcript
        update_task_status(task_id, "processing", {"step": "fetching_transcript"})
        transcript = get_transcript(video_id)

        if len(transcript) < 50:
            raise ValueError("Transcript is too short")

        transcript_len = len(transcript)
        print(f"📏 Transcript length: {transcript_len} chars")

        # Step 3: Determine tier & role modifier
        role_instructions = {
            "child": "\n\n🧒 AUDIENCE: CHILD (Under 13). Write in VERY SIMPLE language. Use fun analogies, cartoons, stories. Explain like talking to a 10-year-old. Use lots of emojis. Break complex ideas into tiny steps. Add 'Fun Fact!' sections.",
            "student": "\n\n🎓 AUDIENCE: STUDENT. Write in clear, educational language. Include step-by-step explanations, study tips, and exam-oriented key points. Use diagrams descriptions, mnemonics, and practice questions where possible.",
            "teacher": "\n\n👨‍🏫 AUDIENCE: TEACHER/EDUCATOR. Write in professional academic language. Include pedagogical insights, teaching methodologies, curriculum connections, and discussion prompts. Add references and further reading suggestions. Be thorough and authoritative.",
            "industry": "\n\n💼 AUDIENCE: INDUSTRY PROFESSIONAL. Write in professional, technical language. Include business implications, ROI analysis, implementation strategies, and industry best practices. Use data-driven insights and actionable recommendations. Be concise yet comprehensive."
        }
        role_modifier = role_instructions.get(user_role, role_instructions["student"])

        notes = None

        # ═══════ TIER 1: SHORT VIDEO (< 12K chars, ~< 15 min) ═══════
        if transcript_len <= SHORT_THRESHOLD:
            print("📗 Tier: SHORT — sending full transcript")
            update_task_status(task_id, "processing", {"step": "generating_notes_short_video"})
            
            prompt = GEMINI_PROMPT.replace("{language}", req.output_language).replace("TRANSCRIPT_PLACEHOLDER", transcript)
            
            if req.model == "qwen":
                notes = await generate_notes_with_qwen3(transcript, req.output_language, role_modifier)
            else:
                notes = await generate_notes_with_gemini(transcript, GEMINI_API_KEY, req.output_language, role_modifier)
                if not notes:
                    print("⚠️ Gemini failed, falling back to Qwen...")
                    notes = await generate_notes_with_qwen3(transcript, req.output_language, role_modifier)

        # ═══════ TIER 2: MEDIUM VIDEO (12K-50K chars, ~15-60 min) ═══════
        elif transcript_len <= LONG_THRESHOLD:
            print(f"📘 Tier: MEDIUM — chunking transcript ({transcript_len} chars)")
            chunks = chunk_transcript(transcript)
            total_chunks = len(chunks)
            print(f"📦 Split into {total_chunks} chunks")
            
            chunk_notes_list = []
            for i, chunk in enumerate(chunks, 1):
                update_task_status(task_id, "processing", {"step": f"generating_chunk_{i}_of_{total_chunks}"})
                print(f"🔄 Processing chunk {i}/{total_chunks} ({len(chunk)} chars)")
                
                chunk_prompt = CHUNK_SUMMARY_PROMPT.format(
                    chunk_num=i, total_chunks=total_chunks,
                    language=req.output_language, transcript=chunk
                )
                
                chunk_result = await generate_for_model(chunk_prompt, req.model, req.output_language, role_modifier)
                if chunk_result:
                    chunk_notes_list.append(chunk_result)
                else:
                    print(f"⚠️ Chunk {i} failed, skipping...")
                
                # Small delay between chunks to respect rate limits
                if i < total_chunks:
                    await asyncio.sleep(2)
            
            if not chunk_notes_list:
                raise ValueError("All chunks failed to generate notes")
            
            # Merge chunk notes
            update_task_status(task_id, "processing", {"step": "merging_notes"})
            combined = "\n\n---\n\n".join(chunk_notes_list)
            
            if len(chunk_notes_list) == 1:
                notes = chunk_notes_list[0]
            else:
                merge_prompt = MERGE_PROMPT.format(language=req.output_language, chunk_notes=combined)
                notes = await generate_for_model(merge_prompt, req.model, req.output_language, "")
                
                # If merge fails, just concatenate
                if not notes:
                    print("⚠️ Merge failed, concatenating chunk notes...")
                    notes = f"# 📺 Video Notes\n\n{combined}"

        # ═══════ TIER 3: LONG VIDEO (> 50K chars, ~> 60 min) ═══════
        else:
            print(f"📕 Tier: LONG — extracting key points only ({transcript_len} chars)")
            chunks = chunk_transcript(transcript)
            total_chunks = len(chunks)
            print(f"📦 Split into {total_chunks} chunks (key-points mode)")
            
            chunk_notes_list = []
            for i, chunk in enumerate(chunks, 1):
                update_task_status(task_id, "processing", {"step": f"extracting_keypoints_{i}_of_{total_chunks}"})
                print(f"🔑 Extracting key points from chunk {i}/{total_chunks} ({len(chunk)} chars)")
                
                chunk_prompt = KEY_POINTS_PROMPT.format(
                    chunk_num=i, total_chunks=total_chunks,
                    language=req.output_language, transcript=chunk
                )
                
                chunk_result = await generate_for_model(chunk_prompt, req.model, req.output_language, role_modifier)
                if chunk_result:
                    chunk_notes_list.append(chunk_result)
                else:
                    print(f"⚠️ Chunk {i} key-points failed, skipping...")
                
                # Longer delay for long videos to respect rate limits
                if i < total_chunks:
                    await asyncio.sleep(3)
            
            if not chunk_notes_list:
                raise ValueError("All chunks failed to extract key points")
            
            # Merge key points
            update_task_status(task_id, "processing", {"step": "merging_key_points"})
            combined = "\n\n---\n\n".join(chunk_notes_list)
            
            if len(chunk_notes_list) == 1:
                notes = chunk_notes_list[0]
            else:
                merge_prompt = MERGE_PROMPT.format(language=req.output_language, chunk_notes=combined)
                notes = await generate_for_model(merge_prompt, req.model, req.output_language, "")
                
                if not notes:
                    print("⚠️ Merge failed, concatenating key points...")
                    notes = f"# 📺 Video Notes (Key Points)\n\n{combined}"

        if not notes:
            raise ValueError("AI generation failed with selected model")

        # Step 4: Save History
        update_task_status(task_id, "processing", {"step": "saving_history"})
        title_line = notes.split('\n')[0][:80].strip('#').strip() if notes else "Untitled Notes"
        
        note_id = secrets.token_hex(8)
        history_entry = {
            "id": note_id,
            "title": title_line,
            "video_id": video_id,
            "youtube_url": req.youtube_url,
            "language": req.output_language,
            "notes": notes,
            "transcript_length": transcript_len,
            "created_at": datetime.utcnow().isoformat()
        }
        save_history_item(user_email, history_entry)
        
        # Complete
        result_payload = {
            "notes": notes, 
            "video_id": video_id, 
            "note_id": note_id,
            "title": title_line
        }
        update_task_status(task_id, "completed", result=result_payload)

    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        update_task_status(task_id, "failed", error=str(e))


def create_token(email: str, name: str) -> str:
    """Create a JWT token for the user."""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "name": name,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats, including encoded URLs."""
    # Step 1: Decode any URL-encoded characters (%3F -> ?, %3D -> =, etc.)
    url = unquote(url).strip()
    
    # Step 2: Try parsing as a proper URL first (most reliable)
    try:
        parsed = urlparse(url)
        if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed.path == '/watch':
                qs = parse_qs(parsed.query)
                if 'v' in qs:
                    vid = qs['v'][0]
                    if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                        return vid
            # Handle /embed/, /shorts/, /v/ paths
            for prefix in ('/embed/', '/shorts/', '/v/'):
                if parsed.path.startswith(prefix):
                    vid = parsed.path[len(prefix):].split('/')[0].split('?')[0]
                    if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                        return vid
        elif parsed.hostname == 'youtu.be':
            vid = parsed.path.lstrip('/').split('/')[0].split('?')[0]
            if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                return vid
    except Exception:
        pass
    
    # Step 3: Fallback regex patterns for edge cases
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise HTTPException(
        status_code=400,
        detail="Invalid YouTube URL. Please provide a valid YouTube video link."
    )

def get_transcript(video_id: str) -> str:
    """Fetch transcript with 3 fallback methods to bypass YouTube cloud IP blocks."""
    cookies_content = os.getenv("YOUTUBE_COOKIES")
    proxy_url = os.getenv("YOUTUBE_PROXY")
    cookie_file_path = None
    
    if cookies_content:
        try:
            fd, cookie_file_path = tempfile.mkstemp(suffix=".txt", text=True)
            with os.fdopen(fd, "w") as f:
                f.write(cookies_content)
        except Exception as e:
            print(f"⚠️ Failed to create cookie file: {e}")

    try:
        # ─── Method 1: youtube-transcript-api v1.2+ ───
        try:
            api = YouTubeTranscriptApi()
            transcript_result = None
            try:
                transcript_result = api.fetch(video_id, languages=['en'])
            except Exception:
                try:
                    transcript_result = api.fetch(video_id)
                except Exception:
                    pass
            
            if transcript_result and transcript_result.snippets:
                full_text = " ".join([s.text for s in transcript_result.snippets])
                if full_text.strip():
                    print(f"✅ Method 1 (youtube-transcript-api): {len(full_text)} chars")
                    return full_text
            
            raise Exception("Empty result")
        except Exception as e:
            print(f"⚠️ Method 1 failed: {e}")

        # ─── Method 2: YouTube Innertube Player API (bypasses watch page) ───
        try:
            print("🔄 Trying innertube player API...")
            innertube_url = "https://www.youtube.com/youtubei/v1/player"
            payload = {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20241201.00.00",
                        "hl": "en",
                        "gl": "US",
                    }
                },
                "videoId": video_id,
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            
            resp = httpx.post(innertube_url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
            
            if not captions:
                raise Exception("No caption tracks in innertube response")
            
            # Prefer English, but take any available
            caption_url = None
            for track in captions:
                if track.get("languageCode", "").startswith("en"):
                    caption_url = track.get("baseUrl")
                    break
            if not caption_url:
                caption_url = captions[0].get("baseUrl")
            
            if not caption_url:
                raise Exception("No caption URL found")
            
            # Add fmt=json3 for JSON format
            if "fmt=" not in caption_url:
                caption_url += "&fmt=json3"
            
            cap_resp = httpx.get(caption_url, headers=headers, timeout=15)
            cap_resp.raise_for_status()
            
            # Try JSON3 format
            try:
                cap_json = cap_resp.json()
                events = cap_json.get("events", [])
                texts = []
                for event in events:
                    for seg in event.get("segs", []):
                        text = seg.get("utf8", "").strip()
                        if text and text != "\n":
                            texts.append(text)
                if texts:
                    full_text = " ".join(texts)
                    print(f"✅ Method 2 (innertube JSON3): {len(full_text)} chars")
                    return full_text
            except (json.JSONDecodeError, ValueError):
                pass
            
            # Fallback: parse XML captions
            import xml.etree.ElementTree as ET
            content = cap_resp.text
            try:
                root = ET.fromstring(content)
                texts = []
                for elem in root.iter("text"):
                    if elem.text:
                        text = elem.text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
                        texts.append(text.strip())
                if texts:
                    full_text = " ".join(texts)
                    print(f"✅ Method 2 (innertube XML): {len(full_text)} chars")
                    return full_text
            except ET.ParseError:
                pass
            
            raise Exception("Could not parse innertube captions")
        except Exception as e:
            print(f"⚠️ Method 2 (innertube) failed: {e}")

        # ─── Method 3: yt-dlp fallback ───
        try:
            print("🔄 Trying yt-dlp fallback...")
            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'quiet': True,
                'no_warnings': True,
                'ignore_no_formats_error': True,
                'format': 'best',
            }
            if cookie_file_path:
                ydl_opts['cookiefile'] = cookie_file_path
            if proxy_url:
                ydl_opts['proxy'] = proxy_url

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subs = info.get('subtitles') or info.get('automatic_captions')
                
                if subs:
                    sub_entries = subs.get('en') or next(iter(subs.values()), None)
                    if sub_entries:
                        sub_url = None
                        for entry in sub_entries:
                            if entry.get('ext') == 'json3':
                                sub_url = entry.get('url')
                                break
                        if not sub_url:
                            for entry in sub_entries:
                                if entry.get('ext') == 'vtt':
                                    sub_url = entry.get('url')
                                    break
                        if not sub_url and sub_entries:
                            sub_url = sub_entries[0].get('url')
                        
                        if sub_url:
                            sub_resp = httpx.get(sub_url, timeout=15)
                            sub_resp.raise_for_status()
                            content = sub_resp.text
                            
                            try:
                                sub_json = json.loads(content)
                                events = sub_json.get('events', [])
                                texts = []
                                for event in events:
                                    for seg in event.get('segs', []):
                                        text = seg.get('utf8', '').strip()
                                        if text and text != '\n':
                                            texts.append(text)
                                if texts:
                                    full_text = " ".join(texts)
                                    print(f"✅ Method 3 (yt-dlp): {len(full_text)} chars")
                                    return full_text
                            except (json.JSONDecodeError, AttributeError):
                                pass
                            
                            lines = content.split('\n')
                            text_lines = []
                            for line in lines:
                                line = line.strip()
                                if not line or '-->' in line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or line.isdigit():
                                    continue
                                clean = re.sub(r'<[^>]+>', '', line)
                                if clean.strip():
                                    text_lines.append(clean.strip())
                            if text_lines:
                                full_text = " ".join(text_lines)
                                print(f"✅ Method 3 (yt-dlp VTT): {len(full_text)} chars")
                                return full_text
                    
                    raise Exception("Found subtitles but couldn't extract text")
                else: 
                    raise Exception("No subtitles found via yt-dlp")
        except Exception as e:
            print(f"⚠️ Method 3 (yt-dlp) failed: {e}")

        raise Exception("All 3 transcript methods failed")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Could not retrieve a transcript" in error_msg:
            raise HTTPException(status_code=404, detail="No transcript available (Captions disabled).")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcript: {error_msg}")
    
    finally:
        if cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
            except Exception as e:
                print(f"⚠️ Failed to remove temp cookie file: {e}")



GEMINI_PROMPT = """You are an expert multilingual note-taking assistant with translation capabilities.

The following YouTube video transcript may be in ANY language (Hindi, Tamil, Telugu, Spanish, Japanese, etc.).
Your task: **Understand the transcript in its original language** and generate comprehensive, professional notes **entirely in {language}**.

If the transcript is already in {language}, generate notes directly.
If the transcript is in a DIFFERENT language, translate and generate notes in {language}.

📋 **FORMAT YOUR NOTES EXACTLY LIKE THIS:**

# 📺 Video Notes

## 🎯 Main Topic
[Identify the main subject/theme of the video in {language}]

## 📌 Key Points

### 1️⃣ [First Major Point]
- 📝 **Explanation:** [Detailed explanation in {language}]
- 💡 **Real-time Example:** [Practical, real-world example in {language}]
- 🔑 **Key Takeaway:** [One-line summary in {language}]

### 2️⃣ [Second Major Point]
- 📝 **Explanation:** [Detailed explanation in {language}]
- 💡 **Real-time Example:** [Practical, real-world example in {language}]
- 🔑 **Key Takeaway:** [One-line summary in {language}]

[Continue for ALL major points...]

## 🧠 Important Concepts Explained
| Concept | Definition | Example |
|---------|-----------|---------|
| [Term 1] | [Definition in {language}] | [Example in {language}] |
| [Term 2] | [Definition in {language}] | [Example in {language}] |

## ⚡ Quick Summary
- ✅ [Point 1 in {language}]
- ✅ [Point 2 in {language}]
- ✅ [Point 3 in {language}]

## 🎓 Conclusion
[Summarize the overall message and key learnings in {language}]

---

**CRITICAL RULES:**
1. ALL output text MUST be in **{language}** — every heading, explanation, example, and summary
2. Use plenty of emojis to make notes visually engaging 🎨
3. Every point MUST include a real-time practical example 💡
4. Explain each point in detail, not just one-liners 📖
5. Use tables for comparing concepts 📊
6. Use bold text for important terms ✨
7. Make notes comprehensive — cover EVERY topic discussed in the video
8. Write in clear, simple {language} that anyone can understand
9. Add numbering for all points for easy reference
10. If original transcript uses technical terms, keep them in parentheses alongside the {language} translation

Here is the transcript to analyze:

TRANSCRIPT_PLACEHOLDER
"""

async def generate_notes_with_gemini(transcript: str, api_key: str, language: str = "English", role_modifier: str = "") -> str:
    """Generate detailed notes using Google Gemini AI (Non-blocking)."""
    retries = 3
    base_delay = 2
    loop = asyncio.get_running_loop()

    for attempt in range(retries):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = GEMINI_PROMPT.replace("{language}", language).replace("TRANSCRIPT_PLACEHOLDER", transcript)
            if role_modifier:
                prompt = prompt + role_modifier

            # Run blocking call in executor
            response = await loop.run_in_executor(
                None,
                functools.partial(
                    client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=8192,
                    )
                )
            )

            if response.text:
                return response.text
            return None

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"⚠️ Gemini 429. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
            print(f"⚠️ Gemini failed: {e}")
            # Fallback
            print("🔄 Switching to Qwen fallback...")
            return await generate_notes_with_qwen3(transcript, language, role_modifier)
    
    return await generate_notes_with_qwen3(transcript, language, role_modifier)


async def generate_notes_with_qwen3(transcript: str, language: str = "English", role_modifier: str = "") -> str:
    """Fallback: Generate notes using Qwen3 via Groq Cloud API (Non-blocking)."""
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not set, skipping Qwen")
        return None

    try:
        prompt = GEMINI_PROMPT.replace("{language}", language).replace("TRANSCRIPT_PLACEHOLDER", transcript)
        if role_modifier:
            prompt = prompt + role_modifier

        client = Groq(api_key=GROQ_API_KEY)

        # Try Groq models in order of preference (all free-tier compatible)
        models_to_try = [
            "qwen/qwen3-32b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "mixtral-8x7b-32768",
        ]

        messages = [
            {"role": "system", "content": "You are an expert educational note-taker."},
            {"role": "user", "content": prompt}
        ]

        last_error = None
        loop = asyncio.get_running_loop()

        for model_id in models_to_try:
            try:
                print(f"🤖 Trying Groq model: {model_id}")
                response = await loop.run_in_executor(
                    None,
                    functools.partial(
                        client.chat.completions.create,
                        model=model_id,
                        messages=messages,
                        max_tokens=8192,
                        temperature=0.7,
                    )
                )

                if response.choices and response.choices[0].message.content:
                    print(f"✅ Successfully generated with Groq/{model_id}")
                    return response.choices[0].message.content
                    
            except Exception as model_err:
                last_error = model_err
                print(f"⚠️ Groq model {model_id} failed: {model_err}")
                continue

        print(f"❌ All Groq models failed. Last error: {last_error}")
        return None

    except Exception as e:
        print(f"⚠️ Groq generation failed entirely: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page."""
    return """<html><head><meta http-equiv="refresh" content="0;url=/static/login.html"></head></html>"""

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login page."""
    return """<html><head><meta http-equiv="refresh" content="0;url=/static/login.html"></head></html>"""

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve dashboard page."""
    return """<html><head><meta http-equiv="refresh" content="0;url=/static/dashboard.html"></head></html>"""

@app.post("/api/signup")
@limiter.limit("5/minute")
async def signup(req: SignUpRequest, request: Request):
    """Register a new user."""
    existing_user = get_user(req.email)

    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Hash password and store user
    user_data = {
        "name": req.name or req.email.split("@")[0],
        "password_hash": hash_password(req.password),
        "created_at": datetime.utcnow().isoformat(),
        "last_login": datetime.utcnow().isoformat()
    }
    save_user(req.email, user_data)

    # Generate token
    name = user_data["name"]
    token = create_token(req.email, name)

    return {
        "token": token,
        "email": req.email,
        "name": name,
        "message": "Account created successfully"
    }

@app.post("/api/login")
@limiter.limit("10/minute")
async def login(req: LoginRequest, request: Request):
    """Authenticate a user."""
    user = get_user(req.email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Wrong password or mail id! Please enter valid data"
        )

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Wrong password or mail id! Please enter valid data"
        )

    # Update last login
    user["last_login"] = datetime.utcnow().isoformat()
    save_user(req.email, user)

    token = create_token(req.email, user["name"])

    return {
        "token": token,
        "email": req.email,
        "name": user["name"],
        "message": "Login successful"
    }

@app.post("/api/google-login")
async def google_login(request: Request):
    """Google OAuth login — verify Google ID token and create/login user."""
    try:
        body = await request.json()
        id_token_str = body.get("credential", "")

        if not id_token_str:
            raise HTTPException(status_code=400, detail="Missing Google credential")

        # Verify the ID token
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request())

        email = idinfo.get("email")
        name = idinfo.get("name", email.split("@")[0])
        picture = idinfo.get("picture", "")

        if not email:
            raise HTTPException(status_code=400, detail="Google account has no email")

        # Auto-create user if doesn't exist
        user = get_user(email)
        if not user:
            user = {
                "name": name,
                "password_hash": "",
                "created_at": datetime.utcnow().isoformat(),
                "last_login": datetime.utcnow().isoformat(),
                "photo_url": picture,
                "role": "student",
                "auth_method": "google"
            }
            save_user(email, user)
        else:
            # Update name and photo on every Google login
            updates = {}
            if picture:
                updates["photo_url"] = picture
            updates["name"] = name
            updates["last_login"] = datetime.utcnow().isoformat()
            
            # Merge updates
            user.update(updates)
            save_user(email, user)

        token = create_token(email, name)
        return {
            "token": token,
            "email": email,
            "name": name,
            "photo_url": picture,
            "message": "Google login successful"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google authentication failed: {str(e)}")

@app.post("/api/generate")
@limiter.limit("5/minute")
async def generate_notes(req: GenerateRequest, request: Request, background_tasks: BackgroundTasks):
    """Start asynchronous note generation."""
    
    # 1. Auth
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
        
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    user_email = payload.get("sub")
    
    # 2. Validation
    if not req.youtube_url:
        raise HTTPException(status_code=400, detail="URL required")
        
    # 3. Get User Role
    user_data = get_user(user_email)
    user_role = user_data.get("role", "student") if user_data else "student"

    # 4. Create Task
    task_id = str(uuid.uuid4())
    update_task_status(task_id, "queued")
    
    # 5. Queue Background Task
    background_tasks.add_task(process_note_generation, task_id, req, user_email, user_role)
    
    return {"task_id": task_id, "status": "queued", "message": "Generation started"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Poll for task status."""
    if not db:
        return {"status": "failed", "error": "Database disconnected"}
        
    doc = db.collection("tasks").document(task_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return doc.to_dict()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "YouTube Transcripter", "version": "1.0.0"}

# ═══════ Page Routes ═══════

@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    return """<html><head><meta http-equiv="refresh" content="0;url=/static/profile.html"></head></html>"""

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    return """<html><head><meta http-equiv="refresh" content="0;url=/static/history.html"></head></html>"""

# ═══════ Profile API ═══════

@app.get("/api/profile")
async def get_profile(request: Request):
    """Get user profile data."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(auth_header.split(" ")[1])
    email = payload.get("sub")

    user = get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "name": user.get("name", ""),
        "email": email,
        "dob": user.get("dob", ""),
        "gender": user.get("gender", ""),
        "role": user.get("role", "student"),
        "photo_url": user.get("photo_url", "")
    }

@app.put("/api/profile")
async def update_profile(req: ProfileUpdateRequest, request: Request):
    """Update user profile."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(auth_header.split(" ")[1])
    email = payload.get("sub")

    user = get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.name: user["name"] = req.name
    if req.dob: user["dob"] = req.dob
    if req.gender: user["gender"] = req.gender
    if req.role: user["role"] = req.role
    if req.photo_url: user["photo_url"] = req.photo_url

    save_user(email, user)
    return {"message": "Profile updated", "role": req.role}

@app.post("/api/upload-photo")
async def upload_photo(request: Request, photo: UploadFile = File(...)):
    """Upload profile photo."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(auth_header.split(" ")[1])
    email = payload.get("sub")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(photo.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOADS_DIR / filename

    with open(filepath, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    photo_url = f"/static/uploads/{filename}"

    # Save to user profile
    user = get_user(email)
    if user:
        user["photo_url"] = photo_url
        save_user(email, user)

    return {"photo_url": photo_url}

# ═══════ History API ═══════

@app.get("/api/history")
async def get_history(request: Request):
    """Get user's note history."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(auth_header.split(" ")[1])
    email = payload.get("sub")

    history = get_user_history(email)
    return {"history": history}

@app.delete("/api/history/{note_id}")
async def delete_history_item(note_id: str, request: Request):
    """Delete a specific note from history."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(auth_header.split(" ")[1])
    email = payload.get("sub")

    delete_history_item_db(email, note_id)
    return {"message": "Note deleted"}

@app.get("/api/cron/check-inactivity")
async def check_inactivity():
    """Check for users inactive for >24h and send emails."""
    if not db:
        return {"message": "Database not connected"}
        
    users_ref = db.collection("users").stream()
    count = 0
    now = datetime.utcnow()
    
    for doc in users_ref:
        data = doc.to_dict()
        email = doc.id
        last_login_str = data.get("last_login")
        if not last_login_str:
            continue
            
        try:
            last_login = datetime.fromisoformat(last_login_str)
            if (now - last_login) > timedelta(hours=24):
                print(f"User {email} inactive for >24h. Sending mail...")
                send_inactivity_email(email)
                count += 1
        except ValueError:
            continue
            
    return {"message": f"Checked inactivity. Emails sent: {count}"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting YouTube Transcripter...")
    print("📍 Open http://localhost:8000 in your browser")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
