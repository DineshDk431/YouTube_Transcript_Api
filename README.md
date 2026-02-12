# 🎬 YouTube Transcripter

> **AI-Powered Notes Generator** — Transform any YouTube video into detailed, emoji-rich study notes with real-world examples using Google Gemini AI.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📸 Features

| Feature | Description |
|---------|-------------|
| 🔐 **User Authentication** | Secure signup/login with JWT tokens and bcrypt password hashing |
| 🐼 **Animated Panda** | Interactive panda character on login — eyes follow typing, closes eyes on password, shakes head on error |
| 📺 **YouTube Integration** | Paste any YouTube URL to auto-extract video transcript |
| 🤖 **AI Notes Generation** | Google Gemini AI creates detailed, structured notes with emojis and real-world examples |
| 📋 **Copy & Download** | One-click copy to clipboard or download notes as Markdown file |
| 🎨 **Premium Dark UI** | Glassmorphism, 3D animations, floating orbs, scroll-reveal effects |
| 📱 **Responsive Design** | Works beautifully on desktop, tablet, and mobile |

---

## 🏗️ Project Structure

```
Youtube_transcript/
├── main.py                    # FastAPI backend server
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── SKILLS.md                  # Skills & technologies used
├── users.json                 # User store (auto-created)
└── static/
    ├── login.html             # Login/Signup page
    ├── dashboard.html         # Main dashboard page
    ├── css/
    │   ├── login.css          # Login page styles
    │   └── style.css          # Dashboard styles
    └── js/
        ├── login.js           # Login page interactions & panda animation
        └── app.js             # Dashboard logic & API calls
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- A Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Step 1: Clone & Navigate
```bash
cd Youtube_transcript
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

### Step 4: Run the Server
```bash
python main.py
```

### Step 5: Open in Browser
```
http://localhost:8000
```

---

## 🔄 How It Works — Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER WORKFLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 🔐 Login/Signup                                        │
│     └── User creates account or logs in                    │
│     └── JWT token stored in localStorage                   │
│                                                             │
│  2. 📺 Paste YouTube URL                                   │
│     └── Video preview auto-embeds                          │
│     └── Enter Gemini API key (saved locally)               │
│                                                             │
│  3. 🚀 Click "Generate Notes"                              │
│     └── Backend extracts video transcript                  │
│     └── Transcript sent to Gemini AI                       │
│     └── AI generates structured, emoji-rich notes          │
│                                                             │
│  4. 📋 View, Copy, or Download                             │
│     └── Notes rendered as beautiful Markdown               │
│     └── Copy to clipboard or download as .md               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Backend Processing Pipeline

```
YouTube URL
    │
    ▼
┌──────────────────┐
│ Extract Video ID │ ← Regex pattern matching
│ (supports 5+     │   (watch, youtu.be, embed,
│  URL formats)    │    shorts, /v/ formats)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Fetch Transcript │ ← youtube_transcript_api
│ (auto-generated  │   Handles missing captions,
│  or manual)      │   unavailable videos
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Gemini AI Prompt │ ← Structured prompt with:
│ (gemini-1.5-     │   • Emoji formatting rules
│  flash model)    │   • Point-by-point structure
│                  │   • Real-world examples
│                  │   • Summary tables
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Return Markdown  │ → Rendered in frontend
│ Notes to Client  │   with full styling
└──────────────────┘
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Redirect to login page | ❌ |
| `GET` | `/dashboard` | Redirect to dashboard | ❌ |
| `POST` | `/api/signup` | Create new account | ❌ |
| `POST` | `/api/login` | Login & get JWT token | ❌ |
| `POST` | `/api/generate` | Generate notes from YouTube URL | ✅ JWT |
| `GET` | `/api/health` | Health check | ❌ |

### Example: Generate Notes
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "api_key": "YOUR_GEMINI_API_KEY"
  }'
```

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
- Processing animation with step indicators
- Beautiful Markdown rendering for AI notes
- Sticky navbar with blur effect

---

## 🔒 Security

- **Passwords** — Hashed with bcrypt (never stored in plain text)
- **Authentication** — JWT tokens with 24-hour expiry
- **API Keys** — Stored only in browser localStorage (never sent to our server storage)
- **Input Validation** — All inputs sanitized and validated

---

## 📝 License

This project is open source under the **MIT License**.

---

<p align="center">
  <b>Built with ❤️ using FastAPI, Google Gemini AI & Vanilla JavaScript</b>
</p>
