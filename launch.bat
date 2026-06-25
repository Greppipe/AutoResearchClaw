@echo off
setlocal enabledelayedexpansion
title SCI Research Platform

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "SENTINEL=%ROOT%.setup_done"
set "ENV_FILE=%ROOT%.env.local"
set "TESSERACT=C:\Program Files\Tesseract-OCR\tesseract.exe"

cls
echo.
echo  +============================================================+
echo  ^|          SCI Research Platform  v2.0                      ^|
echo  ^|          AI-Powered Journal Paper Generator               ^|
echo  +============================================================+
echo.

:: ═══════════════════════════════════════════════════════════════
::  PHASE 1 — ONE-TIME SETUP  (skipped on all future runs)
:: ═══════════════════════════════════════════════════════════════

if exist "%SENTINEL%" if exist "%PYTHON%" goto :check_keys

echo  First launch detected. Setting up automatically...
echo  (This takes 10-20 minutes once. Every run after this is instant.)
echo.

:: ── 1a. Python (must be 3.10–3.13; 3.14+ has no pre-built wheels) ──
echo  [1/6] Checking Python version...
set "SYSPYTHON="

:: Try py launcher: prefer 3.12, then 3.11, then 3.10, then 3.13
for %%v in (3.12 3.11 3.10 3.13) do (
    if "!SYSPYTHON!"=="" (
        py -%%v --version >nul 2>&1
        if not errorlevel 1 (
            set "SYSPYTHON=py -%%v"
            for /f "tokens=2 delims= " %%V in ('py -%%v --version 2^>^&1') do (
                echo        [OK] Found Python %%V via py launcher.
            )
        )
    )
)

:: Fallback: check default python, but reject 3.14+
if "!SYSPYTHON!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
        for /f "tokens=1 delims=." %%a in ("!PYVER!") do set PYMAJ=%%a
        for /f "tokens=2 delims=." %%b in ("!PYVER!") do set PYMIN=%%b
        if !PYMAJ! EQU 3 if !PYMIN! LEQ 13 (
            set "SYSPYTHON=python"
            echo        [OK] Found Python !PYVER!
        ) else (
            echo        [WARN] Python !PYVER! detected but packages require 3.10-3.13.
        )
    )
)

:: If still nothing, install Python 3.11
if "!SYSPYTHON!"=="" (
    echo        Compatible Python not found. Installing Python 3.11 automatically...
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\py_setup.exe' -UseBasicParsing; Write-Host 'Download complete.'"
    "%TEMP%\py_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    del "%TEMP%\py_setup.exe" >nul 2>&1
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        set "SYSPYTHON=py -3.11"
        echo        [OK] Python 3.11 installed.
    ) else (
        echo        ERROR: Could not install Python. Please install 3.11 from https://python.org
        pause & exit /b 1
    )
)

:: ── 1b. Virtual environment ───────────────────────────────────
echo  [2/6] Creating virtual environment...
if not exist "%VENV%\Scripts\activate.bat" (
    !SYSPYTHON! -m venv "%VENV%"
    if errorlevel 1 ( echo        ERROR: venv creation failed. & pause & exit /b 1 )
)
call "%VENV%\Scripts\activate.bat"
"%PYTHON%" -m pip install --upgrade pip wheel setuptools --quiet
echo        [OK] Virtual environment ready.

:: ── 1c. Python packages ──────────────────────────────────────
echo  [3/6] Installing Python packages (one-time, ~5-10 min)...

echo        Stage A: Core essentials + AI...
"%PIP%" install "python-dotenv" "rich" "questionary" "structlog" "pydantic" "pydantic-settings" "httpx" "requests" --quiet
"%PIP%" install "anthropic==0.28.0" "langchain==0.2.5" "langchain-anthropic==0.1.15" "langchain-community==0.2.5" "langchain-core==0.2.9" "langgraph==0.1.14" "langsmith==0.1.77" "tavily-python==0.3.3" --quiet
"%PIP%" install "langchain-groq" "langchain-ollama" "langchain-google-genai" --quiet
echo        Stage B: ML and embeddings...
"%PIP%" install "sentence-transformers==3.0.1" "scikit-learn==1.5.0" "numpy==1.26.4" "scipy==1.13.0" --quiet
echo        Stage C: Document processing...
"%PIP%" install "pymupdf==1.24.5" "python-docx==1.1.2" "pytesseract==0.3.10" "Pillow==10.3.0" "opencv-python-headless==4.9.0.80" "tabula-py==2.9.3" --quiet
echo        Stage D: Charts, data, utilities...
"%PIP%" install "matplotlib==3.9.0" "seaborn==0.13.2" "pandas==2.2.2" "openpyxl==3.1.4" --quiet
echo        Stage E: All remaining packages...
"%PIP%" install -r "%ROOT%requirements.cli.txt" --quiet
echo        Stage F: Optional extras...
"%PIP%" install "camelot-py[cv]" --quiet >nul 2>&1
"%PIP%" install "tika" --quiet >nul 2>&1
echo        [OK] All packages installed.

:: ── 1d. System tools ─────────────────────────────────────────
echo  [4/6] Installing system tools (Tesseract, Java, Ghostscript)...
winget --version >nul 2>&1
if not errorlevel 1 (
    winget install --id UB-Mannheim.TesseractOCR   -e --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    winget install --id Microsoft.OpenJDK.21        -e --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    winget install --id ArtifexSoftware.GhostScript -e --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    echo        [OK] System tools installed.
) else (
    echo        [SKIP] winget not available. Tesseract/Java/Ghostscript can be added later.
)

:: ── 1e. Pre-download AI models ───────────────────────────────
echo  [5/6] Downloading AI embedding models (~800MB total, ONE-TIME only)...
echo        You will see download progress below. Do NOT close this window.
echo.
"%PYTHON%" -u -c "print('  Downloading all-mpnet-base-v2 (Deep Document Intelligence)...',flush=True);from sentence_transformers import SentenceTransformer;SentenceTransformer('all-mpnet-base-v2');print('  [OK] all-mpnet-base-v2 ready.',flush=True);print('  Downloading all-MiniLM-L6-v2 (Plagiarism detection)...',flush=True);SentenceTransformer('all-MiniLM-L6-v2');print('  [OK] all-MiniLM-L6-v2 ready.',flush=True)"
if errorlevel 1 echo        [WARN] Model download incomplete. Will retry automatically on first run.

:: ── 1f. Mark setup complete ──────────────────────────────────
echo  [6/6] Finalising setup...
echo %date% %time% > "%SENTINEL%"
echo        [OK] Setup complete. This step will never run again.
echo.

:: ═══════════════════════════════════════════════════════════════
::  PHASE 2 — API KEYS  (only when missing or placeholder)
:: ═══════════════════════════════════════════════════════════════

:check_keys

:: Activate venv (needed for subsequent runs where setup was skipped)
call "%VENV%\Scripts\activate.bat" >nul 2>&1

if not exist "%ENV_FILE%" goto :ask_keys

:: Check if file has LLM_PROVIDER set (means setup already done properly)
findstr /i "LLM_PROVIDER=" "%ENV_FILE%" >nul 2>&1
if not errorlevel 1 goto :launch

:: Legacy check for old .env.local without LLM_PROVIDER
findstr /i "REPLACE-ME" "%ENV_FILE%" >nul 2>&1
if not errorlevel 1 goto :ask_keys

goto :launch

:ask_keys
echo  +------------------------------------------------------------+
echo  ^|  Choose your AI provider  (choose FREE options below)     ^|
echo  +------------------------------------------------------------+
echo.
echo  FREE options:
echo    1. Ollama  (runs on YOUR PC, 100%% free, already installed)
echo       Best model: llama3.1:8b  or  qwen2.5:14b
echo.
echo    2. Groq    (free API, very fast)
echo       Sign up free at: https://console.groq.com/
echo.
echo    3. Gemini  (free API, 1500 requests/day)
echo       Sign up free at: https://aistudio.google.com/
echo.
echo  PAID option:
echo    4. Anthropic Claude (best quality, ~$3-7 per paper)
echo       Get key at: https://console.anthropic.com/
echo.
set /p PROVIDER_CHOICE="  Enter choice (1/2/3/4) [default=1 Ollama]: "
if "!PROVIDER_CHOICE!"=="" set PROVIDER_CHOICE=1

if "!PROVIDER_CHOICE!"=="1" (
    set LLM_PROVIDER=ollama
    echo.
    echo  Using Ollama (local, free^).
    echo  Make sure a model is downloaded. Run in a new terminal:
    echo    ollama pull llama3.1:8b
    echo.
    set AKEY=not-needed
    set /p TKEY="  Paste TAVILY_API_KEY for web search (tvly-... or press Enter to skip): "
    if "!TKEY!"=="" set TKEY=tvly-skip
)

if "!PROVIDER_CHOICE!"=="2" (
    set LLM_PROVIDER=groq
    echo.
    set /p AKEY="  Paste GROQ_API_KEY (gsk_...): "
    if "!AKEY!"=="" ( echo  ERROR: GROQ_API_KEY is required. & pause & exit /b 1 )
    set /p TKEY="  Paste TAVILY_API_KEY (tvly-... or press Enter to skip): "
    if "!TKEY!"=="" set TKEY=tvly-skip
)

if "!PROVIDER_CHOICE!"=="3" (
    set LLM_PROVIDER=gemini
    echo.
    set /p AKEY="  Paste GEMINI_API_KEY (AIza...): "
    if "!AKEY!"=="" ( echo  ERROR: GEMINI_API_KEY is required. & pause & exit /b 1 )
    set /p TKEY="  Paste TAVILY_API_KEY (tvly-... or press Enter to skip): "
    if "!TKEY!"=="" set TKEY=tvly-skip
)

if "!PROVIDER_CHOICE!"=="4" (
    set LLM_PROVIDER=anthropic
    echo.
    set /p AKEY="  Paste ANTHROPIC_API_KEY (sk-ant-...): "
    if "!AKEY!"=="" ( echo  ERROR: ANTHROPIC_API_KEY is required. & pause & exit /b 1 )
    set /p TKEY="  Paste TAVILY_API_KEY (tvly-...): "
    if "!TKEY!"=="" set TKEY=tvly-skip
)

:: Write .env.local
(
echo LLM_PROVIDER=!LLM_PROVIDER!
if "!LLM_PROVIDER!"=="anthropic" echo ANTHROPIC_API_KEY=!AKEY!
if "!LLM_PROVIDER!"=="groq"      echo GROQ_API_KEY=!AKEY!
if "!LLM_PROVIDER!"=="gemini"    echo GEMINI_API_KEY=!AKEY!
echo TAVILY_API_KEY=!TKEY!
) > "%ENV_FILE%"

if exist "%TESSERACT%" (
    echo TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe>> "%ENV_FILE%"
)

echo  [OK] Provider saved as !LLM_PROVIDER!. Will never be asked again.
echo.

:: ═══════════════════════════════════════════════════════════════
::  PHASE 2b — LICENSE KEY  (only when .license file is missing)
:: ═══════════════════════════════════════════════════════════════

if exist "%ROOT%.license" goto :launch

:: Check if license validation is active (PUBLIC_KEY_PEM != DEV_MODE)
"%PYTHON%" -c "
import sys
sys.path.insert(0, r'%ROOT%backend')
try:
    from app.license import PUBLIC_KEY_PEM
    if PUBLIC_KEY_PEM == b'DEV_MODE':
        sys.exit(0)   # Dev mode — skip license check
    else:
        sys.exit(1)   # Production — need license
except Exception:
    sys.exit(0)
" >nul 2>&1
if errorlevel 1 (
    echo  +------------------------------------------------------------+
    echo  ^|  License Key Required                                     ^|
    echo  ^|  Purchase at: https://yoursite.com                        ^|
    echo  +------------------------------------------------------------+
    echo.
    set /p LKEY="  Paste your license key: "
    if "!LKEY!"=="" ( echo  ERROR: License key is required. & pause & exit /b 1 )

    "%PYTHON%" -c "
import sys
sys.path.insert(0, r'%ROOT%backend')
from app.license import save_license
ok, msg = save_license('!LKEY!')
print(f'  {msg}')
sys.exit(0 if ok else 1)
"
    if errorlevel 1 ( echo  Invalid license key. & pause & exit /b 1 )
    echo  [OK] License saved.
    echo.
)

:: ═══════════════════════════════════════════════════════════════
::  PHASE 3 — LAUNCH WIZARD
:: ═══════════════════════════════════════════════════════════════

:launch
cd /d "%ROOT%"
echo  Starting research wizard...
echo.
"%PYTHON%" run.py
if errorlevel 1 (
    echo.
    echo  Something went wrong. Error details are shown above.
    echo  Common fixes:
    echo    - Check your API keys in .env.local
    echo    - Delete .setup_done and re-run launch.bat to reinstall
    echo.
    pause
)
endlocal
