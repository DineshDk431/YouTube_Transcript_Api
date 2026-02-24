# 🎬 YouTube Transcripter

> **AI-Powered Notes Generator** — Paste any YouTube URL and get detailed, structured study notes instantly. Handles videos of any length.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=flat-square&logo=google&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=flat-square&logo=firebase&logoColor=black)

---

## ✨ Features

- 🔐 **Secure Auth** — Signup/Login with JWT + Google OAuth
- 🤖 **Dual AI** — Google Gemini 2.0 Flash (primary) + Qwen3 via Groq (fallback)
- 📏 **Any Video Length** — Smart chunking for short clips to 3-hour lectures
- 🌍 **Multilingual** — Generate notes in any language
- 👥 **Role-Based** — Tailored notes for Child, Student, Teacher, or Professional
- 📥 **Download** — Copy or download notes as Markdown
- 📜 **History** — All notes saved per user in Firebase
- 🎨 **Premium UI** — Dark glassmorphism theme with animated panda login

---

## � How It Works

```mermaid
flowchart TD
    A["🔗 Paste YouTube URL"] --> B["🔍 Extract Video ID"]
    B --> C["📜 Fetch Transcript"]
    
    C --> D["Method 1: youtube-transcript-api"]
    C --> E["Method 2: Innertube API (5 clients)"]
    C --> F["Method 3: yt-dlp"]
    
    D -->|Success| G["📏 Detect Video Length"]
    E -->|Success| G
    F -->|Success| G
    
    D -->|All Failed| H["🎬 Gemini Direct Mode"]
    E -->|All Failed| H
    F -->|All Failed| H
    
    H --> K["✨ AI Notes Generated"]

    G --> G1["📗 Short < 15 min"]
    G --> G2["📘 Medium 15-60 min"]
    G --> G3["📕 Long > 60 min"]
    
    G1 -->|"Full transcript"| I["🤖 AI Generation"]
    G2 -->|"Chunk → Summarize → Merge"| I
    G3 -->|"Chunk → Key Points → Merge"| I
    
    I --> J{"Model Selection"}
    J -->|Primary| J1["Gemini 2.0 Flash"]
    J -->|Fallback| J2["Qwen3-32B via Groq"]
    
    J1 --> K
    J2 --> K
    
    K --> L["💾 Save to Firebase"]
    L --> M["📥 Display & Download Notes"]

    style A fill:#667eea,color:#fff
    style K fill:#48bb78,color:#fff
    style H fill:#ed8936,color:#fff
    style M fill:#667eea,color:#fff
```

---

## �🚀 Quick Start

```bash
# Clone
git clone https://github.com/DineshDk431/YouTube_Transcript_Api.git
cd YouTube_Transcript_Api

# Install
pip install -r requirements.txt

# Configure .env
GEMINI_API_KEY=your-key
GROQ_API_KEY=your-key
SECRET_KEY=your-secret
FIREBASE_CREDENTIALS=serviceAccountKey.json
GOOGLE_CLIENT_ID=your-client-id

# Run
python main.py
# Open http://localhost:8000
```

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| AI Models | Google Gemini 2.0 Flash, Qwen3-32B (Groq) |
| Database | Firebase Firestore |
| Auth | JWT + Google OAuth |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Render (free tier) |

---

## 🚀 Deploy on Render

Set these environment variables on Render:

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq Cloud API key |
| `SECRET_KEY` | JWT signing secret |
| `FIREBASE_CREDENTIALS` | `serviceAccountKey.json` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |

---

## 📝 License

MIT License

<p align="center"><b>Built with ❤️ by Dinesh</b></p>
