# 🎬 YouTube Transcripter

> **AI-Powered Notes Generator** — Transform any YouTube video into detailed, emoji-rich study notes with real-world examples. Supports videos of **any length** — from 1-minute clips to 3-hour lectures.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_Cloud-Qwen3-FF6B35?style=for-the-badge&logo=groq&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📸 Features

| Feature | Description |
|---------|-------------|
| 🔐 **User Authentication** | Secure signup/login with JWT tokens + Google OAuth support |
| 🐼 **Animated Panda** | Interactive panda on login — eyes follow typing, closes eyes on password, shakes head on error |
| 📺 **YouTube Integration** | Paste any YouTube URL (supports standard, short, embed, mobile & encoded URLs) |
| 🤖 **Dual AI Models** | Choose between **Google Gemini 2.0 Flash** or **Qwen3-32B via Groq Cloud** |
| 📏 **Any Video Length** | Smart chunking system handles short clips to 3+ hour lectures |
| 🌍 **Multilingual** | Generate notes in any language — English, Hindi, Tamil, Spanish, Japanese, etc. |
| 👥 **Role-Based Notes** | Tailored for Child 🧒, Student 🎓, Teacher 👨‍🏫, or Industry Professional 💼 |
| 📋 **Copy & Download** | One-click copy to clipboard or download notes as Markdown |
| 📜 **History** | Full history of generated notes stored in Firebase |
| 🎨 **Premium Dark UI** | Glassmorphism, 3D animations, floating orbs, scroll-reveal effects |
| 📱 **Responsive Design** | Works beautifully on desktop, tablet, and mobile |

---

## 🧠 Smart Chunking — Any Video Length

The app uses a **tiered strategy** to handle videos of any duration:

| Tier | Video Length | Transcript Size | Strategy |
|------|------------|-----------------|----------|
| 📗 **Short** | < 15 min | < 12K chars | Full transcript → detailed notes |
| 📘 **Medium** | 15–60 min | 12K–50K chars | Split into chunks → summarize each → merge into one doc |
| 📕 **Long** | > 60 min | 50K+ chars | Split into chunks → extract **key points only** → merge important notes |

- **Sentence-boundary splitting** — chunks never cut mid-sentence
- **Overlapping chunks** — 500-char overlap prevents context loss
- **Live progress** — UI shows "Processing section 3 of 7..." in real-time
- **Graceful fallback** — if one chunk fails, the rest still process

---

## 🏗️ Project Structure

```
Youtube_transcript/
├── main.py                    # FastAPI backend (AI pipeline, auth, chunking)
├── firebase_config.py         # Firebase/Firestore initialization
├── serviceAccountKey.json     # Firebase service account (not committed)
├── requirements.txt           # Python dependencies
├── render.yaml                # Render deployment config
├── .env                       # Environment variables (not committed)
├── .dockerignore              # Docker ignore rules
├── .gitignore                 # Git ignore rules
└── static/
    ├── login.html             # Login/Signup page
    ├── dashboard.html         # Main dashboard page
    ├── profile.html           # User profile page
    ├── history.html           # Notes history page
    ├── css/
    │   ├── login.css          # Login page styles
    │   └── style.css          # Dashboard styles
    └── js/
        ├── login.js           # Login page interactions & panda animation
        ├── app.js             # Dashboard logic, polling & chunk progress
        ├── profile.js         # Profile page logic
        └── history.js         # History page logic
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- A **Google Gemini API key** ([Get one here](https://aistudio.google.com/apikey))
- A **Groq Cloud API key** ([Get one here — free, no card](https://console.groq.com))
- A **Firebase project** with Firestore enabled

### Step 1: Clone & Navigate
```bash
git clone https://github.com/DineshDk431/YouTube_Transcript_Api.git
cd YouTube_Transcript_Api
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key
SECRET_KEY=your-random-secret-key
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FIREBASE_CREDENTIALS=serviceAccountKey.json
GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

### Step 5: Run the Server
```bash
python main.py
```

### Step 6: Open in Browser
```
http://localhost:8000
```

---

## 🔄 How It Works — Processing Pipeline

```
YouTube URL
    │
    ▼
┌───────────────────────┐
│ 1. URL Decode & Parse │ ← unquote() + urlparse()
│    Extract Video ID   │   Handles encoded URLs (%3F, %3D)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 2. Fetch Transcript   │ ← youtube_transcript_api
│    + yt-dlp fallback  │   Supports cookies & proxy
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 3. Detect Video Tier  │
│  Short / Medium / Long│ ← Based on transcript char count
└──────────┬────────────┘
           │
     ┌─────┼─────────────────────┐
     ▼     ▼                     ▼
  SHORT  MEDIUM                LONG
  Full   Chunk → Summarize   Chunk → Key Points
  Send   → Merge             → Merge
     │     │                     │
     └─────┼─────────────────────┘
           │
           ▼
┌───────────────────────┐
│ 4. AI Generation      │ ← Gemini 2.0 Flash (primary)
│    with Fallback      │   Qwen3-32B via Groq (fallback)
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 5. Save to Firestore  │ → History stored per user
│    Return Notes       │   Rendered as rich Markdown
└───────────────────────┘
```

---

## 🤖 AI Models

| Model | Provider | Context Window | Use Case |
|-------|----------|---------------|----------|
| **Gemini 2.0 Flash** | Google AI | 1M tokens | Primary — fast, high quality |
| **Qwen3-32B** | Groq Cloud | 131K tokens | Fallback — free tier, fast inference |
| **Llama 4 Scout** | Groq Cloud | 131K tokens | Secondary fallback |
| **Mixtral 8x7B** | Groq Cloud | 32K tokens | Tertiary fallback |

> Models are tried in order. If Gemini hits rate limits (429), the system automatically falls back to Qwen3 via Groq.

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Redirect to login page | ❌ |
| `GET` | `/dashboard` | Redirect to dashboard | ❌ |
| `GET` | `/profile` | User profile page | ❌ |
| `GET` | `/history` | Notes history page | ❌ |
| `POST` | `/api/signup` | Create new account | ❌ |
| `POST` | `/api/login` | Login & get JWT token | ❌ |
| `POST` | `/api/google-login` | Google OAuth login | ❌ |
| `POST` | `/api/generate` | Start async note generation | ✅ JWT |
| `GET` | `/api/tasks/{id}` | Poll for generation status | ❌ |
| `GET` | `/api/profile` | Get user profile data | ✅ JWT |
| `PUT` | `/api/profile` | Update user profile | ✅ JWT |
| `POST` | `/api/upload-photo` | Upload profile photo | ✅ JWT |
| `GET` | `/api/history` | Get user's note history | ✅ JWT |
| `DELETE` | `/api/history/{id}` | Delete a note from history | ✅ JWT |
| `GET` | `/api/health` | Health check | ❌ |
| `GET` | `/api/cron/check-inactivity` | Check/email inactive users | ❌ |

### Example: Generate Notes
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "output_language": "English",
    "model": "gemini"
  }'
```

Response:
```json
{
  "task_id": "uuid-here",
  "status": "queued",
  "message": "Generation started"
}
```

Then poll `GET /api/tasks/{task_id}` until `status` is `"completed"`.

---

## 🎨 UI Highlights

### Login Page 🐼
- Animated SVG panda character with eye tracking
- Panda closes eyes when typing password
- Panda shakes head left-right on wrong credentials
- 3D card tilt effect on mouse move
- Floating particle background

### Dashboard Page 🎯
- 3D floating gradient orbs with parallax
- Scroll-reveal animations on all sections
- Real-time YouTube video preview embed
- **Live chunk processing progress** — "Processing section 3 of 7..."
- Beautiful Markdown rendering for AI notes
- Sticky navbar with blur effect

---

## � Deployment (Render)

The app is configured for **Render free tier** deployment.

### Environment Variables on Render

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GROQ_API_KEY` | Your Groq Cloud API key |
| `SECRET_KEY` | Random secret for JWT signing |
| `SMTP_EMAIL` | Gmail address for inactivity emails |
| `SMTP_PASSWORD` | Gmail app password |
| `FIREBASE_CREDENTIALS` | `serviceAccountKey.json` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `PYTHON_VERSION` | `3.10.0` |

---

## �🔒 Security

- **Passwords** — SHA-256 hashed with random salt (never stored in plain text)
- **Authentication** — JWT tokens with 24-hour expiry
- **Google OAuth** — ID token verified server-side
- **Rate Limiting** — 5 req/min on signup, 10 req/min on login, 5 req/min on generate
- **Input Validation** — All inputs sanitized and validated
- **CORS** — Configurable allowed origins

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `google-genai` | Gemini AI SDK |
| `groq` | Groq Cloud SDK (Qwen3, Llama, Mixtral) |
| `youtube-transcript-api` | Fetch YouTube transcripts |
| `yt-dlp` | Fallback transcript fetching |
| `firebase-admin` | Firestore database |
| `python-jose` | JWT token handling |
| `slowapi` | Rate limiting |
| `httpx` | Async HTTP client |

---

## 📝 License

This project is open source under the **MIT License**.

---

<p align="center">
  <b>Built with ❤️ using FastAPI, Google Gemini AI, Groq Cloud, Firebase & Vanilla JavaScript</b>
</p>
