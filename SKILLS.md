# 🛠️ SKILLS.md — Technologies & Skills Used

> A comprehensive breakdown of every technology, skill, and tool used to build the **YouTube Transcripter** application.

## 🐍 Backend Skills

### 1. Python 3.10+
- **Core Language** for the entire backend
- Async/await for non-blocking API calls
- Type hints with Pydantic models
- File I/O for JSON-based user storage
- Regular expressions for URL parsing

### 2. FastAPI
- High-performance async web framework
- Automatic API documentation (Swagger UI at `/docs`)
- Pydantic request/response validation
- Static file serving for frontend assets
- CORS middleware configuration
- HTTPException for structured error responses
- Dependency injection system

### 3. JWT Authentication (python-jose)
- Token-based authentication system
- HS256 algorithm for signing
- 24-hour token expiry
- Secure payload encoding/decoding

### 4. Password Security (passlib + bcrypt)
- Industry-standard bcrypt hashing
- Secure password verification
- No plain-text password storage

### 5. YouTube Transcript API
- Automated transcript extraction from YouTube videos
- Support for auto-generated and manual captions
- Error handling for unavailable videos/transcripts

### 6. Google Gemini AI (google-generativeai)
- `gemini-1.5-flash` model integration
- Prompt engineering for structured note output
- Temperature and token limit configuration
- API key validation and quota handling


## 🎨 Frontend Skills

### 7. HTML5
- Semantic markup (`<nav>`, `<main>`, `<section>`, `<footer>`)
- Embedded SVG for animated panda character
- SEO meta tags and structured headings
- Accessible form elements with labels and placeholders

### 8. CSS3 (Vanilla — No Frameworks)
- **Glassmorphism** — `backdrop-filter: blur()` with transparent backgrounds
- **3D Transforms** — `perspective()`, `rotateX/Y`, `translateZ`
- **CSS Animations** — `@keyframes` for floating orbs, particle effects, shimmer borders
- **CSS Variables** — Custom properties for consistent theming
- **CSS Transitions** — Smooth state changes on hover, focus, and scroll
- **Responsive Design** — `@media` queries for mobile/tablet/desktop
- **Gradient Animations** — Animated `background-position` for buttons
- **Pseudo-elements** — `::before` / `::after` for grain texture and decorative elements

### 9. JavaScript (Vanilla ES6+)
- **DOM Manipulation** — `getElementById`, `querySelector`, `setAttribute`
- **Event Handling** — `click`, `focus`, `blur`, `input`, `scroll`, `submit`
- **Fetch API** — Async HTTP requests to backend with JWT headers
- **IntersectionObserver** — Scroll-reveal animations (3D card fly-in)
- **LocalStorage** — Token persistence, API key caching, user data
- **SVG Manipulation** — Direct attribute changes for panda eye/hand animations
- **Markdown Renderer** — Custom regex-based Markdown → HTML converter
- **Template Literals** — Dynamic HTML generation
- **Clipboard API** — `navigator.clipboard.writeText()` for copy feature
- **Blob/URL API** — File download for Markdown notes

## 🎭 Animation & Design Skills

### 10. SVG Animation
- Hand-crafted SVG panda character (~100 lines of SVG)
- Eye pupil tracking via JavaScript `translate()` transforms
- Eyelid close animation via SVG attribute changes (`cy`, `ry`)
- Head shake animation via CSS `@keyframes`
- Body bounce and ear wiggle idle animations

### 11. 3D CSS Effects
- `perspective()` for depth on login card
- `rotateX/Y` mouse-tracking tilt effect
- `translateZ` for parallax orb movement
- `transform-style: preserve-3d` for nested 3D

### 12. Micro-Animations
- Toast notification slide-in/slide-out
- Button hover glow with `box-shadow` transitions
- Shimmer border effect with moving gradients
- Input focus underline animation with `scaleX`
- Processing spinner with rotating rings

## 🏛️ Architecture & Patterns

### 13. REST API Design
- RESTful endpoint naming (`/api/signup`, `/api/login`, `/api/generate`)
- HTTP status codes (200, 400, 401, 404, 409, 429, 500, 501)
- JSON request/response format
- Bearer token authentication pattern

### 14. MVC-like Separation
- **Model** — Pydantic schemas + JSON user store
- **View** — Static HTML/CSS/JS pages
- **Controller** — FastAPI route handlers

### 15. Security Practices
- Password hashing (bcrypt)
- JWT token expiry
- Input validation (Pydantic)
- CORS configuration
- API key isolation (client-side only)

### 16. Error Handling
- Structured error responses with `HTTPException`
- Frontend toast notifications for all error states
- Graceful fallbacks (network errors, invalid URLs, missing transcripts)

---

## 📦 Dependencies Summary

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn` | 0.30.0 | ASGI server |
| `youtube_transcript_api` | 0.6.3 | Transcript extraction |
| `google-generativeai` | 0.8.0 | Gemini AI integration |
| `python-jose` | 3.3.0 | JWT tokens |
| `passlib` | 1.7.4 | Password hashing |
| `python-multipart` | 0.0.9 | Form data parsing |

---

## 🧰 Tools Used

| Tool | Purpose |
|------|---------|
| **VS Code** | Code editor |
| **Python venv** | Virtual environment |
| **pip** | Package manager |
| **Git** | Version control |
| **Chrome DevTools** | Frontend debugging |
| **Google AI Studio** | Gemini API key generation |

---

<p align="center">
  <b>Total Skills Used: 16+ across Backend, Frontend, Animation, Architecture & Security</b>
</p>
