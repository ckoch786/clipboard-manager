# Remove old backup if it exists
if (Test-Path clipman-release-old) {
    Remove-Item -Recurse -Force clipman-release-old
}

# Move current release to old if it exists
if (Test-Path clipman-release) {
    Move-Item clipman-release clipman-release-old -Force
}

# Create new release directory
mkdir clipman-release
mkdir clipman-release/assets

# Copy files from dist folder (PyInstaller creates dist/clipman/ directory)
Copy-Item dist/clipman/clipman.exe clipman-release/clipman.exe
Copy-Item assets/clipboard.png clipman-release/assets/clipboard.png
