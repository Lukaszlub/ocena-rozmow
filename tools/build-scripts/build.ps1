$ErrorActionPreference = "Stop"

# Build one-folder executable for Windows
pip install -r requirements.txt
pip install -r requirements-build.txt

pyinstaller `
  --noconsole `
  --name "OcenaRozmow" `
  --add-data "config.yaml;." `
  --add-data "src;src" `
  src/app/entry.py

Write-Host "Build complete: dist\\OcenaRozmow"
