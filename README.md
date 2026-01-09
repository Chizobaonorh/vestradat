# VestraDAT - Body Measurement API

AI-powered body measurement tool using computer vision with Cloudinary integration.

## Quick Start

### Local Development
```bash
py app_working.py
```

### API Testing
**Endpoint:** `POST http://localhost:5000/measure`

**Option 1: Cloudinary URLs (Recommended)**
```json
{
  "frontImageUrl": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/front.jpg",
  "sideImageUrl": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/side.jpg",
  "userHeight": 170
}
```

**Option 2: Base64 (Legacy Support)**
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
- **Cloudinary Integration** - Direct URL processing (recommended)
- **Base64 Support** - Legacy compatibility
- Real image processing with OpenCV
- Height-based scaling
- Memory-optimized for production
- Automatic image resizing
- Production-ready deployment

## Benefits of Cloudinary Integration
- **Reduced Memory Usage** - No base64 encoding/decoding
- **Faster Processing** - Direct image download
- **Better Performance** - Optimized image delivery
- **Automatic Optimization** - Cloudinary handles compression
- **CDN Benefits** - Global image delivery