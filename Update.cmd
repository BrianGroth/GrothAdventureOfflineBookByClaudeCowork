@echo off
setlocal
rem ============================================================
rem  Update.cmd - pull new blog posts and refresh the offline
rem  book folder.
rem
rem  Usage:   Update.cmd [output-folder]
rem  Example: Update.cmd E:\GrothBook
rem  Default output: data\exports\static-book
rem
rem  Fast: only posts you don't have yet are downloaded, and
rem  only new photos are copied into the book folder.
rem  Needs internet for the download step.
rem ============================================================

cd /d "%~dp0"

set "OUT=%~1"
if "%OUT%"=="" set "OUT=data\exports\static-book"

echo.
echo === Groth Adventures offline book: update ===
echo Book folder: %OUT%
echo.

echo [1/3] Checking the blog for new posts...
scrapbook sync --source grothadventures
if errorlevel 1 goto :fail

echo [2/3] Re-applying book chapters...
python scripts\assign_topics.py
if errorlevel 1 goto :fail

echo [3/3] Refreshing the book folder...
scrapbook export --format static-book --output "%OUT%"
if errorlevel 1 goto :fail

echo.
echo === Done ===
echo If step 2 listed posts with no chapter, give each one a chapter in
echo scripts\assign_topics.py and run this file again. Until then those
echo posts appear in the temporary "New Adventures" chapter.
echo.
pause
exit /b 0

:fail
echo.
echo Something went wrong - see the message above.
pause
exit /b 1
