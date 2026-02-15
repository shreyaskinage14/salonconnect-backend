@echo off
echo Running migrations...
alembic upgrade head
IF %ERRORLEVEL% NEQ 0 (
  echo Migration failed!
  exit /b %ERRORLEVEL%
)

echo Starting server...
uvicorn app.main:app --host 0.0.0.0 --port 8000
