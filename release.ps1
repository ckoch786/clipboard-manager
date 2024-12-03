Move-Item clipman-release clipman-release-old -Force
mkdir clipman-release
mkdir clipman-release/assets
Copy-Item dist/clipman.exe clipman-release/clipman.exe
Copy-Item assets/clipboard.png clipman-release/assets/clipboard.png
