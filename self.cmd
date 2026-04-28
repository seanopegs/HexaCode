@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

if "%PORT%"=="" set "PORT=8080"
if "%HOST%"=="" set "HOST=0.0.0.0"

set "PYTHON_VERSION=3.12.10"
set "RUNTIME_HOME=%~dp0.runtime"
set "PYTHON_DIR=%RUNTIME_HOME%\python-%PYTHON_VERSION%-embed-amd64"
set "PYTHON_ZIP=%RUNTIME_HOME%\python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"

if /I "%~1"=="stop" goto :stop_server
if /I "%~1"=="check" goto :check_runtime

echo ==========================================
echo HexaCare self-host starter
echo ==========================================
echo.
echo [INFO] Root     : %CD%
echo [INFO] Database : %CD%\database\hexacare.sqlite3
echo [INFO] URL      : http://127.0.0.1:%PORT%/
echo.

call :find_python
if errorlevel 1 (
  echo [ERROR] Python gagal disiapkan.
  pause
  exit /b 1
)

echo [INFO] Menggunakan Python: %PYTHON_CMD%
set "OPEN_BROWSER=1"
echo.
echo [INFO] Tekan Ctrl+C untuk menghentikan server.
echo.

if "%PYTHON_IS_LAUNCHER%"=="1" (
  "%PYTHON_CMD%" -3 -u app.py
) else (
  "%PYTHON_CMD%" -u app.py
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Server berhenti dengan kode %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%

:check_runtime
echo ==========================================
echo HexaCare runtime check
echo ==========================================
echo.
call :find_python
if errorlevel 1 (
  echo [ERROR] Python valid tidak ditemukan.
  exit /b 1
)
echo [OK] Python valid: %PYTHON_CMD%
if "%PYTHON_IS_LAUNCHER%"=="1" (
  "%PYTHON_CMD%" -3 -c "import sqlite3; print('sqlite3 ok')"
) else (
  "%PYTHON_CMD%" -c "import sqlite3; print('sqlite3 ok')"
)
exit /b %ERRORLEVEL%

:find_python
set "PYTHON_CMD="
set "PYTHON_IS_LAUNCHER=0"

for %%I in (python.exe) do set "PYTHON_CMD=%%~$PATH:I"
if defined PYTHON_CMD (
  echo "!PYTHON_CMD!" | findstr /I "\\WindowsApps\\python.exe" >nul
  if not errorlevel 1 set "PYTHON_CMD="
)
if defined PYTHON_CMD (
  call :validate_python "!PYTHON_CMD!"
  if not errorlevel 1 exit /b 0
  set "PYTHON_CMD="
)

for %%I in (py.exe) do set "PYTHON_CMD=%%~$PATH:I"
if defined PYTHON_CMD (
  set "PYTHON_IS_LAUNCHER=1"
  call :validate_py_launcher "!PYTHON_CMD!"
  if not errorlevel 1 exit /b 0
  set "PYTHON_CMD="
  set "PYTHON_IS_LAUNCHER=0"
)

if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  set "PYTHON_CMD=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  call :validate_python "!PYTHON_CMD!"
  if not errorlevel 1 exit /b 0
  set "PYTHON_CMD="
)

if exist "%PYTHON_DIR%\python.exe" (
  set "PYTHON_CMD=%PYTHON_DIR%\python.exe"
  call :validate_python "!PYTHON_CMD!"
  if not errorlevel 1 exit /b 0
  set "PYTHON_CMD="
)

echo [INFO] Python tidak ditemukan. Menyiapkan Python portable %PYTHON_VERSION%...
call :install_portable_python
if errorlevel 1 exit /b 1

set "PYTHON_CMD=%PYTHON_DIR%\python.exe"
if not exist "%PYTHON_CMD%" exit /b 1
call :validate_python "!PYTHON_CMD!"
if errorlevel 1 exit /b 1
exit /b 0

:validate_python
%~1 -c "import sqlite3, sys; print(sys.version.split()[0])" >nul 2>nul
exit /b %ERRORLEVEL%

:validate_py_launcher
%~1 -3 -c "import sqlite3, sys; print(sys.version.split()[0])" >nul 2>nul
exit /b %ERRORLEVEL%

:install_portable_python
if not exist "%RUNTIME_HOME%" mkdir "%RUNTIME_HOME%"

echo [INFO] Mengunduh Python portable...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"
if errorlevel 1 exit /b 1

echo [INFO] Mengekstrak Python portable...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%RUNTIME_HOME%' -Force"
if errorlevel 1 exit /b 1

if exist "%RUNTIME_HOME%\python-%PYTHON_VERSION%-embed-amd64\python.exe" (
  exit /b 0
)

echo [ERROR] File python.exe portable tidak ditemukan setelah ekstrak.
exit /b 1

:stop_server
set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "PORT_PID=%%P"
  goto :pid_found
)

:pid_found
if not defined PORT_PID (
  echo [INFO] Tidak ada server aktif di port %PORT%.
  exit /b 0
)

echo [INFO] Menghentikan server PID %PORT_PID% di port %PORT%...
taskkill /PID %PORT_PID% /F
exit /b %ERRORLEVEL%
