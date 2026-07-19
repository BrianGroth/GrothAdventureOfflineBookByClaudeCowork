@echo off
setlocal
rem ============================================================
rem  InitialRun.cmd - first-time build of the Groth Adventures
rem  offline book, end to end: install tools, download the blog,
rem  assign chapters, build the app, and write the shareable
rem  book folder.
rem
rem  Usage:   InitialRun.cmd [output-folder]
rem  Example: InitialRun.cmd E:\GrothBook
rem  Default output: data\exports\static-book
rem
rem  Needs internet. Requires Python (python.org) and
rem  Node.js (nodejs.org) to be installed first.
rem  Safe to re-run: finished steps are skipped or fast.
rem ============================================================

cd /d "%~dp0"

set "OUT=%~1"
if "%OUT%"=="" set "OUT=data\exports\static-book"

echo.
echo === Groth Adventures offline book: initial build ===
echo Output folder: %OUT%
echo.

where python >nul 2>&1
if errorlevel 1 goto :nopython

rem --- Step 1: install the scrapbook command if missing ---
where scrapbook >nul 2>&1
if not errorlevel 1 goto :have_cli
echo [1/6] Installing the scrapbook command...
pip install -e .
if errorlevel 1 goto :fail
goto :cli_done
:have_cli
echo [1/6] scrapbook command already installed - skipping.
:cli_done

echo [2/6] Preparing the local database...
scrapbook init
if errorlevel 1 goto :fail

echo [3/6] Downloading blog posts and photos...
scrapbook sync --source grothadventures
if errorlevel 1 goto :fail

echo [4/6] Assigning posts to book chapters...
python scripts\assign_topics.py
if errorlevel 1 goto :fail

rem --- Step 5: build the web app only if not built yet ---
if exist app\dist\index.html goto :have_app
echo [5/6] Building the web app...
where npm >nul 2>&1
if errorlevel 1 goto :nonode
cd app
call npm install
if errorlevel 1 goto :fail_in_app
call npm run build
if errorlevel 1 goto :fail_in_app
cd ..
goto :app_done
:have_app
echo [5/6] Web app already built - skipping.
:app_done

echo [6/6] Writing the shareable book folder...
scrapbook export --format static-book --output "%OUT%"
if errorlevel 1 goto :fail

echo.
echo === Done ===
echo Your offline book is in: %OUT%
echo Copy that folder anywhere - USB stick, cloud drive, another PC.
echo To read it: open the folder and double-click index.html
echo.
pause
exit /b 0

:nopython
echo ERROR: Python was not found.
echo Install it from https://www.python.org/downloads/
echo IMPORTANT: tick "Add python.exe to PATH" during install.
echo Then run this file again.
pause
exit /b 1

:nonode
echo ERROR: Node.js was not found.
echo Install it from https://nodejs.org/ then run this file again.
pause
exit /b 1

:fail_in_app
cd ..
:fail
echo.
echo Something went wrong - see the message above.
pause
exit /b 1
