@echo off
REM Construye el AnoniPRO portable para Windows 10/11 (64 bits).
REM DEBE ejecutarse en un Windows (PyInstaller no cross-compila desde Mac).
REM No requiere permisos de administrador: Python "embeddable"/normal de usuario basta.
REM
REM Preparacion (una vez, desde la carpeta del proyecto):
REM   python -m venv .venv
REM   .venv\Scripts\pip install -r backend\requirements.txt pyinstaller
REM   .venv\Scripts\python -m spacy download es_core_news_lg
REM
REM Uso:
REM   herramientas\construir_portable_windows.bat

cd /d "%~dp0\.."

REM Limpia la construccion anterior: sin esto, si PyInstaller falla, el dist\
REM viejo se queda y la comprobacion final da un falso "todo correcto".
if exist dist\AnoniPRO rmdir /s /q dist\AnoniPRO

REM --collect-all para spaCy y sus dependencias compiladas: PyInstaller no
REM detecta solo los modulos en C (spacy.symbols, thinc, blis...).
.venv\Scripts\pyinstaller --noconfirm --clean ^
  --name AnoniPRO ^
  --onedir ^
  --console ^
  --paths backend ^
  --add-data "frontend;frontend" ^
  --collect-all es_core_news_lg ^
  --collect-all spacy ^
  --collect-all thinc ^
  --collect-all blis ^
  --collect-all srsly ^
  --collect-all preshed ^
  --collect-all cymem ^
  --collect-all murmurhash ^
  --collect-all wasabi ^
  --collect-all catalogue ^
  --collect-all confection ^
  --collect-data presidio_analyzer ^
  --collect-submodules uvicorn ^
  --collect-submodules app ^
  --hidden-import cymem ^
  --hidden-import cymem.cymem ^
  backend\portable_main.py

REM Comprobacion 1: PyInstaller debe haber terminado bien
if errorlevel 1 (
  echo.
  echo ERROR: PyInstaller fallo. Revisa los mensajes de arriba.
  echo   - Si pone "no se reconoce el comando": falta ejecutar
  echo     .venv\Scripts\pip install pyinstaller
  echo No distribuyas nada de dist\.
  exit /b 1
)

REM Comprobacion 2: el ejecutable debe existir
if not exist dist\AnoniPRO\AnoniPRO.exe (
  echo ERROR: no se genero dist\AnoniPRO\AnoniPRO.exe. No lo distribuyas. & exit /b 1
)

REM Comprobacion 3: cymem debe estar dentro del paquete
dir /b /s dist\AnoniPRO\_internal\cymem*.pyd >nul 2>&1 || (
  echo ERROR: cymem no quedo dentro del paquete. No lo distribuyas. & exit /b 1
)

echo.
echo Portable creado en: dist\AnoniPRO\
echo Ejecutable:         dist\AnoniPRO\AnoniPRO.exe
echo Para distribuirlo:  comprime la carpeta dist\AnoniPRO en un .zip
echo.
echo El usuario final solo descomprime y hace doble clic en AnoniPRO.exe
echo (sin instalacion y sin permisos de administrador).
echo OCR opcional para escaneados: instalar Tesseract para Windows (UB Mannheim),
echo tambien disponible sin admin eligiendo una carpeta de usuario.
