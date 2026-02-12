import json
import os
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import JWTError, jwt
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types

SECRET_KEY = "yt-transcripter-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
USERS_FILE = Path("users.json")

def hash_password(password: str) -> str:
    """Hash password with SHA-256 + random salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    salt, hashed = stored_hash.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed

app = FastAPI(
    title="YouTube Transcripter",
    description="AI-powered notes generator from YouTube videos",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    api_key: str
    output_language: str = "English"

def load_users() -> dict:
    """Load users from JSON file."""
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

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
    """Extract YouTube video ID from various URL formats."""
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
    """Fetch transcript for a YouTube video."""
    try:
        ytt = YouTubeTranscriptApi()
        transcript_data = ytt.fetch(video_id)
        full_text = " ".join([entry.text for entry in transcript_data])
        return full_text
    except Exception as e:
        error_msg = str(e)
        if "Could not retrieve a transcript" in error_msg or "NoTranscript" in error_msg or "TranscriptsDisabled" in error_msg:
            raise HTTPException(
                status_code=404,
                detail="No transcript available for this video. The video may not have captions enabled."
            )
        elif "Video unavailable" in error_msg or "VideoUnavailable" in error_msg:
            raise HTTPException(
                status_code=404,
                detail="Video not found or is unavailable."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch transcript: {error_msg}"
            )

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

async def generate_notes_with_gemini(transcript: str, api_key: str, language: str = "English") -> str:
    """Generate detailed notes using Google Gemini AI."""
    try:
        client = genai.Client(api_key=api_key)

        prompt = GEMINI_PROMPT.replace("{language}", language).replace("TRANSCRIPT_PLACEHOLDER", transcript)

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )

        if response.text:
            return response.text
        else:
            raise HTTPException(
                status_code=500,
                detail="Gemini returned an empty response. Try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Invalid Gemini API key. Please check your API key and try again."
            )
        elif "quota" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please try again later or use a different API key."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"AI generation failed: {error_msg}"
            )

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
async def signup(req: SignUpRequest):
    """Register a new user."""
    users = load_users()

    if req.email in users:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Hash password and store user
    users[req.email] = {
        "name": req.name or req.email.split("@")[0],
        "password_hash": hash_password(req.password),
        "created_at": datetime.utcnow().isoformat()
    }
    save_users(users)

    # Generate token
    name = users[req.email]["name"]
    token = create_token(req.email, name)

    return {
        "token": token,
        "email": req.email,
        "name": name,
        "message": "Account created successfully"
    }

@app.post("/api/login")
async def login(req: LoginRequest):
    """Authenticate a user."""
    users = load_users()

    if req.email not in users:
        raise HTTPException(
            status_code=401,
            detail="Wrong password or mail id! Please enter valid data"
        )

    user = users[req.email]
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Wrong password or mail id! Please enter valid data"
        )

    token = create_token(req.email, user["name"])

    return {
        "token": token,
        "email": req.email,
        "name": user["name"],
        "message": "Login successful"
    }

@app.post("/api/google-login")
async def google_login():
    """Google OAuth login (placeholder — requires OAuth Client ID setup)."""
    raise HTTPException(
        status_code=501,
        detail="Google Sign-In requires OAuth Client ID configuration. Use email/password for now."
    )

@app.post("/api/generate")
async def generate_notes(req: GenerateRequest, request: Request):
    """Generate AI-powered notes from a YouTube video."""

    # Verify auth token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header.split(" ")[1]
    verify_token(token)

    # Validate inputs
    if not req.youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    if not req.api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is required")

    # Step 1: Extract video ID
    video_id = extract_video_id(req.youtube_url)

    # Step 2: Fetch transcript
    transcript = get_transcript(video_id)

    if len(transcript) < 50:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short to generate meaningful notes."
        )
        
    if len(transcript) > 30000:
        transcript = transcript[:30000] + "... [transcript truncated for processing]"

    # Step 3: Generate notes with Gemini AI
    notes = await generate_notes_with_gemini(transcript, req.api_key, req.output_language)

    return {
        "notes": notes,
        "video_id": video_id,
        "transcript_length": len(transcript),
        "message": "Notes generated successfully"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "YouTube Transcripter", "version": "1.0.0"}
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting YouTube Transcripter...")
    print("📍 Open http://localhost:8000 in your browser")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
