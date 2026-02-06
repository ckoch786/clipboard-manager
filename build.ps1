# Clean
if (Test-Path .\dist) {
    Remove-Item -Recurse -Force .\dist
}

# Build
python -m PyInstaller '.\clipman.py' `
    --icon .\assets\clipboard.png `
    #--windowed `
    #--add-data ".\assets\clipboard.png:.\assets\clipboard.png"

# Copy assets to dist until figure out how to include them in the exe
mkdir .\dist\clipman\assets
Copy-Item .\assets\clipboard.png .\dist\clipman\assets\clipboard.png

# Run
.\dist\clipman\clipman.exe