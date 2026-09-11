@echo off
REM Construye ARAEMKA Redact portable para Windows 10/11 de 64 bits.
REM DEBE ejecutarse en Windows: PyInstaller no cross-compila desde macOS.
REM
REM El resultado incluye Tesseract OCR y los modelos espanol e ingles. El
REM usuario final no necesita instalar Python, Tesseract ni ninguna libreria.
REM
REM Preparacion (una vez, desde la carpeta del proyecto):
REM   py -3.12 -m venv .venv
REM   .venv\Scripts\pip install -r backend\requirements.txt pyinstaller
REM   .venv\Scripts\python -m spacy download es_core_news_md
REM   .venv\Scripts\python -m spacy download en_core_web_md
REM
REM Tambien debe estar instalado Tesseract para construir el paquete, con los
REM idiomas Spanish y English. Se puede indicar otra ubicacion con:
REM   set ANONIPRO_TESSERACT_DIR=C:\ruta\Tesseract-OCR

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."

echo.
echo ==== ARAEMKA Redact - portable Windows con OCR ====

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: falta el entorno .venv. Sigue la preparacion indicada al principio.
  exit /b 1
)

REM ── Localizar Tesseract y comprobar los dos idiomas ──────────────────
set "TESSERACT_DIR=%ANONIPRO_TESSERACT_DIR%"
if not defined TESSERACT_DIR if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" set "TESSERACT_DIR=%ProgramFiles%\Tesseract-OCR"
if not defined TESSERACT_DIR if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" set "TESSERACT_DIR=%ProgramFiles(x86)%\Tesseract-OCR"
if not defined TESSERACT_DIR if exist "%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe" set "TESSERACT_DIR=%LOCALAPPDATA%\Tesseract-OCR"
if not defined TESSERACT_DIR (
  for /f "delims=" %%T in ('where tesseract.exe 2^>nul') do if not defined TESSERACT_DIR set "TESSERACT_DIR=%%~dpT"
)

if not defined TESSERACT_DIR (
  echo ERROR: Tesseract no esta instalado en la maquina de construccion.
  echo Instala Tesseract 5 para Windows con los idiomas Spanish y English.
  exit /b 1
)
if not exist "%TESSERACT_DIR%\tesseract.exe" (
  echo ERROR: no existe "%TESSERACT_DIR%\tesseract.exe".
  exit /b 1
)
if not exist "%TESSERACT_DIR%\tessdata\spa.traineddata" (
  echo ERROR: falta el idioma espanol: %TESSERACT_DIR%\tessdata\spa.traineddata
  exit /b 1
)
if not exist "%TESSERACT_DIR%\tessdata\eng.traineddata" (
  echo ERROR: falta el idioma ingles: %TESSERACT_DIR%\tessdata\eng.traineddata
  exit /b 1
)
echo OCR encontrado en: %TESSERACT_DIR%

REM ── Preparar una copia minima y autocontenida de Tesseract ───────────
set "TESS_STAGE=build\tesseract-portable"
if exist "%TESS_STAGE%" rmdir /s /q "%TESS_STAGE%"
mkdir "%TESS_STAGE%\tessdata" || exit /b 1
copy /y "%TESSERACT_DIR%\tesseract.exe" "%TESS_STAGE%\" >nul || exit /b 1
copy /y "%TESSERACT_DIR%\*.dll" "%TESS_STAGE%\" >nul || (
  echo ERROR: no se pudieron copiar las DLL de Tesseract.
  exit /b 1
)
xcopy /e /i /y "%TESSERACT_DIR%\tessdata" "%TESS_STAGE%\tessdata" >nul || exit /b 1

REM Conservar configuracion, fuentes y solo los modelos necesarios.
for %%F in ("%TESS_STAGE%\tessdata\*.traineddata") do (
  if /I not "%%~nxF"=="spa.traineddata" if /I not "%%~nxF"=="eng.traineddata" if /I not "%%~nxF"=="osd.traineddata" del /q "%%~fF"
)
for %%L in (LICENSE LICENSE.txt TESSDATA-LICENSE.txt COPYING README.md) do if exist "%TESSERACT_DIR%\%%L" copy /y "%TESSERACT_DIR%\%%L" "%TESS_STAGE%\" >nul

REM ── Metadatos e iconos ────────────────────────────────────────────────
.venv\Scripts\python herramientas\generar_iconos.py || exit /b 1
.venv\Scripts\python herramientas\generar_version_windows.py || exit /b 1

REM Limpiar la construccion anterior para evitar falsos positivos.
if exist "dist\ARAEMKA-Redact" rmdir /s /q "dist\ARAEMKA-Redact"

REM Los modelos medianos mantienen NER y reducen cientos de MB de vectores que
REM el portable no necesita. Los hooks oficiales de PyInstaller recopilan spaCy
REM y thinc; las extensiones compiladas restantes se fuerzan explicitamente.
.venv\Scripts\pyinstaller --noconfirm --clean ^
  --name ARAEMKA-Redact ^
  --icon frontend\iconos\icono.ico ^
  --version-file build\version_info_windows.txt ^
  --onedir ^
  --console ^
  --paths backend ^
  --add-data "frontend;frontend" ^
  --add-data "%TESS_STAGE%;tesseract" ^
  --collect-all es_core_news_md ^
  --collect-all en_core_web_md ^
  --collect-all blis ^
  --collect-all srsly ^
  --collect-all preshed ^
  --collect-all cymem ^
  --collect-all murmurhash ^
  --collect-all wasabi ^
  --collect-all catalogue ^
  --collect-all confection ^
  --collect-all openpyxl ^
  --collect-data presidio_analyzer ^
  --collect-submodules uvicorn ^
  --collect-submodules app ^
  --exclude-module pytest ^
  --exclude-module blis.tests ^
  --exclude-module srsly.tests ^
  --exclude-module preshed.tests ^
  --exclude-module cymem.tests ^
  --exclude-module murmurhash.tests ^
  --exclude-module wasabi.tests ^
  --exclude-module catalogue.tests ^
  --hidden-import cymem ^
  --hidden-import cymem.cymem ^
  backend\portable_main.py

if errorlevel 1 (
  echo ERROR: PyInstaller fallo. No distribuyas nada de dist\.
  exit /b 1
)
if not exist "dist\ARAEMKA-Redact\ARAEMKA-Redact.exe" (
  echo ERROR: no se genero dist\ARAEMKA-Redact\ARAEMKA-Redact.exe.
  exit /b 1
)
dir /b /s "dist\ARAEMKA-Redact\_internal\cymem*.pyd" >nul 2>&1 || (
  echo ERROR: cymem no quedo dentro del paquete.
  exit /b 1
)
for %%F in (tesseract.exe tessdata\spa.traineddata tessdata\eng.traineddata) do if not exist "dist\ARAEMKA-Redact\_internal\tesseract\%%F" (
  echo ERROR: falta OCR dentro del paquete: %%F
  exit /b 1
)

copy /y "herramientas\LEEME-WINDOWS.txt" "dist\ARAEMKA-Redact\LEEME PRIMERO.txt" >nul || exit /b 1
copy /y "AVISO-LEGAL.md" "dist\ARAEMKA-Redact\AVISO LEGAL.txt" >nul || exit /b 1
copy /y "LICENSE" "dist\ARAEMKA-Redact\LICENSE.txt" >nul || exit /b 1
copy /y "CODIGO-FUENTE.md" "dist\ARAEMKA-Redact\CODIGO FUENTE.txt" >nul || exit /b 1
copy /y "THIRD-PARTY-NOTICES.md" "dist\ARAEMKA-Redact\COMPONENTES Y LICENCIAS.txt" >nul || exit /b 1
copy /y "TRADEMARKS.md" "dist\ARAEMKA-Redact\MARCAS.txt" >nul || exit /b 1
.venv\Scripts\python herramientas\generar_avisos_terceros.py "dist\ARAEMKA-Redact\LICENCIAS-TERCEROS" || exit /b 1

set "REVISION_CODIGO=sin-revision"
for /f %%G in ('git rev-parse HEAD 2^>nul') do set "REVISION_CODIGO=%%G"
set "ESTADO_CODIGO=limpio"
git diff --quiet --ignore-submodules HEAD 2>nul || set "ESTADO_CODIGO=con-cambios-locales"
(
  echo ARAEMKA Redact
  echo Revision de codigo: !REVISION_CODIGO!
  echo Estado de construccion: !ESTADO_CODIGO!
  echo Codigo fuente: https://github.com/jralbertoalonso-tech/ARAEMKA-Redact
) > "dist\ARAEMKA-Redact\REVISION DE CODIGO.txt"

REM ── Prueba real: arranque, API y OCR de una imagen sintetica ──────────
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "herramientas\probar_portable_windows.ps1"
if errorlevel 1 (
  echo ERROR: el portable no supero la prueba funcional.
  exit /b 1
)

REM ── ZIP final y suma verificable ─────────────────────────────────────
set /p ANONIPRO_VERSION=<"build\VERSION.txt"
if not defined ANONIPRO_VERSION set "ANONIPRO_VERSION=sin-version"
set "ZIP=ARAEMKA-Redact-portable-windows-x64-v%ANONIPRO_VERSION%.zip"
if exist "%ZIP%" del /q "%ZIP%"
if exist "%ZIP%.sha256.txt" del /q "%ZIP%.sha256.txt"
powershell.exe -NoLogo -NoProfile -Command "Compress-Archive -Path 'dist\ARAEMKA-Redact' -DestinationPath '%ZIP%' -CompressionLevel Optimal -Force; $h=(Get-FileHash -Algorithm SHA256 '%ZIP%').Hash.ToLower(); ($h + '  %ZIP%') | Set-Content -Encoding ascii '%ZIP%.sha256.txt'; Write-Host ('SHA-256: ' + $h)"
if errorlevel 1 exit /b 1

echo.
echo ==== PAQUETE TERMINADO Y PROBADO ====
echo ZIP:      %CD%\%ZIP%
echo SHA-256:  %CD%\%ZIP%.sha256.txt
echo OCR:      incluido ^(espanol + ingles^)
echo Firma:    sin firma Authenticode; consulta LEEME PRIMERO.txt
echo.
exit /b 0
