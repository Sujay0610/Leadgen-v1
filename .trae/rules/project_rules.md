always run backend using:
uvicorn main:app --host 0.0.0.0 --port 8000
and not python file directly

don't use curl commands always use:
Invoke-RestMethod -Uri ... command

If you ever want to set-location dont't use cd & 'c:\Users\Sujay S C\Downloads\leadgensupa\backend'
use Set-Location 'c:\Users\Sujay S C\Downloads\leadgensupa\backend'; uvicorn main:app --host 0.0.0.0 --port 8000
