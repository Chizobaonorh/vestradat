# VestraDAT - Body Measurement API

AI-powered body measurement tool using computer vision.

## Quick Start

### Local Development
```bash
py app_working.py
```

### API Testing
**Endpoint:** `POST http://localhost:5000/measure`

**Request:**
```json
{
  "frontImageData": "data:image/jpeg;base64,<BASE64_IMAGE>",
  "sideImageData": "data:image/jpeg;base64,<BASE64_IMAGE>",
  "userHeight": 170
}
```

## Deployment

### Render Deployment
**Start Command:** `gunicorn app_working:app`

**Files:**
- `app_working.py` - Main application (use this, not app.py)
- `requirements.txt` - Dependencies
- `runtime.txt` - Python 3.11.0
- `Procfile` - Deployment config

### Important Notes
- ❌ **Don't use** `app.py` (broken due to MediaPipe API changes)
- ✅ **Use** `app_working.py` (working OpenCV-based solution)
- **Start Command must be:** `gunicorn app_working:app`

## Features
- Real base64 image processing
- OpenCV-based body measurements
- Height-based scaling
- Production-ready deployment