# N.O.V.A — Local Setup Guide

## Prerequisites

- **Python 3.12+** with `venv`
- **Node.js 18+** with `npm`
- macOS (required for TouchID biometric auth)

---

## 1. Start the Backend API Server

```bash
cd /Users/sohamdhande/Docs_Local/NOVA
source venv/bin/activate
python3 main.py
```

Or use the shortcut script:

```bash
cd /Users/sohamdhande/Docs_Local/NOVA
./start.sh
```

You should see:

```
==================================================
  N.O.V.A System Boot Sequence
==================================================
[NOVA] ✓ Encryption ready
[NOVA] ✓ Event Bus running
[NOVA] ✓ System Optimizer running
[NOVA] ✓ Biometric Auth ready
[NOVA] ✓ Browser ready (lazy launch)
[NOVA] ✓ Controller subscribed
[NOVA] ✓ Daemon running
[NOVA] ✓ API Server live on localhost:8000
```

The API is now live at **http://localhost:8000**.

---

## 2. Start the Frontend Dashboard

Open a **second terminal** and run:

```bash
cd /Users/sohamdhande/Docs_Local/NOVA/dashboard
npm run dev
```

You should see:

```
VITE ready in ~200ms

➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173/** in your browser.

---

## 3. Authentication

1. The dashboard shows a **biometric lock screen** on first load
2. Click the **fingerprint icon** to trigger TouchID
3. On success, you enter the dashboard with a 30-minute session

**Password login (fallback):** `nova2026`

---

## 4. Stop Everything

```bash
# Kill backend
pkill -f "python3 main.py"

# Kill frontend
pkill -f "npm run dev"
```

Or kill by port:

```bash
lsof -i :8000 -t | xargs kill -9   # backend
lsof -i :5173 -t | xargs kill -9   # frontend
```

---

## Quick Reference

| Service   | Command                         | URL                    |
|-----------|---------------------------------|------------------------|
| Backend   | `./start.sh`                    | http://localhost:8000   |
| Frontend  | `cd dashboard && npm run dev`   | http://localhost:5173   |
| API Docs  | (auto with backend)             | http://localhost:8000/docs |
