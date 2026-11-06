$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location -LiteralPath $root
$env:TEMP = Join-Path $root 'work\tmp'
$env:TMP = $env:TEMP
$env:PYINSTALLER_CONFIG_DIR = Join-Path $root 'work\pyinstaller-cache'
$env:PYTHONIOENCODING = 'utf-8'
$env:MPLCONFIGDIR = Join-Path $root 'work\mpl-cache'
$env:PYTHONPATH = ''
$env:PATH = (Join-Path $root '.venv\Scripts')+';C:\Windows\System32;C:\Windows'
New-Item -ItemType Directory -Path $env:TEMP,$env:PYINSTALLER_CONFIG_DIR,$env:MPLCONFIGDIR,'D:\workspace\MarklineRuntime' -Force | Out-Null
& (Join-Path $root '.venv\Scripts\python.exe') -m PyInstaller --noconfirm --clean --onefile --windowed --name Markline --icon (Join-Path $root 'resources\Markline.ico') --add-data ((Join-Path $root 'resources')+';.') --runtime-tmpdir 'D:\workspace\MarklineRuntime' --distpath outputs --workpath work\build --specpath work --paths src --exclude-module numpy --exclude-module pandas --exclude-module matplotlib --exclude-module scipy --exclude-module lxml --exclude-module PIL --exclude-module tkinter --exclude-module IPython --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtWebEngineQuick --exclude-module PySide6.QtPdf --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick src\main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
