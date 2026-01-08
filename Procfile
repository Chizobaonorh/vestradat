# FIX: January 7, 2026 - Added resource limits for Render 512MB/0.15CPU
# Prevents 502 Bad Gateway errors with timeout and worker limits
web: gunicorn app_working:app --timeout 60 --workers 1 --max-requests 10
# END FIX: January 7, 2026 - Resource optimization complete