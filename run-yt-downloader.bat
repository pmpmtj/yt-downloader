@echo off
set "PROJ=C:\Users\pmpmt\yt-downloader"
set "PORT=8005"
set "LOG=%PROJ%\logs\devserver.log"
if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"

echo Starting YouTube Downloader...
echo Project directory: %PROJ%
echo Port: %PORT%
echo Log file: %LOG%
echo.

pushd "%PROJ%"

rem Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and ensure it's in your system PATH
    pause
    exit /b 1
)

rem Check if manage.py exists
if not exist "%PROJ%\manage.py" (
    echo ERROR: manage.py not found in %PROJ%
    echo Please ensure you're running this from the correct directory
    pause
    exit /b 1
)

rem Check if virtual environment exists
if not exist "%PROJ%\.venv" (
    echo ERROR: Virtual environment not found at %PROJ%\.venv
    echo Please create a virtual environment first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%PROJ%\.venv\Scripts\activate.bat"

echo Starting Django development server...
echo Press Ctrl+C to stop the server
echo.

rem Run the server and show output in console, also log to file
python "%PROJ%\manage.py" runserver 0.0.0.0:%PORT% --noreload

popd

echo.
echo Server stopped. Press any key to exit...
pause >nul
