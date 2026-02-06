# Clipman

A powerful GUI clipboard manager for Windows with advanced features for organizing and managing your clipboard history.

## Features

### Core Functionality
* **Automatic Clipboard Monitoring**: Continuously monitors and saves clipboard history
* **Search & Filter**: Search clipboard items by content or custom name
* **Multi-Select Operations**: Select and remove multiple items at once
* **Persistent History**: Clipboard history is saved to disk and restored on startup

### Advanced Features
* **📌 Pin Items**: Pin important clipboard items to keep them at the top of the list
* **🏷️ Custom Names**: Give clipboard items custom names for easy identification
* **Preview Window**: Open items in a separate window with JSON pretty-printing support
* **Screen Lock Resilient**: Gracefully handles clipboard access issues when screen is locked
* **Right-Click Context Menu**: Quick access to pin, rename, load, and remove actions

### User Interface
* Dark theme with customizable colors
* Real-time search filtering
* Pin indicators (📌) for pinned items
* Custom names displayed in brackets before item text
* Scrollable list with truncated preview text

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd clipboard
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running

### From Source
```bash
python clipman.py
```

### From Binary
```powershell
.\build.ps1
.\dist\clipman\clipman.exe
```

## Usage

### Basic Operations
- **Copy to Clipboard**: Select an item and click "Load to Clipboard" or double-click
- **Remove Items**: Select one or more items and click "Remove"
- **Search**: Type in the search bar to filter items by text or name
- **View Details**: Double-click any item to open it in a detailed view window

### Pin & Name Items
- **Pin/Unpin**: Select an item and click "Pin/Unpin" button or right-click → "Pin/Unpin"
- **Rename**: Click "Rename" button or right-click → "Rename" to give an item a custom name
- **Pinned Items**: Automatically appear at the top with a 📌 indicator

### Keyboard Shortcuts
- **Enter** (in rename dialog): Save the new name
- **Escape** (in rename dialog): Cancel renaming
- **Double-Click**: Open item in detailed view

## Technical Details

### Architecture
- Built with Python and Tkinter for the GUI
- Uses `pyperclip` for cross-platform clipboard access
- Persistent storage via pickle serialization
- Background thread for continuous clipboard monitoring
- Comprehensive logging to `clipman.log`

### Error Handling
- Graceful handling of clipboard access failures
- Automatic retry with exponential backoff
- Screen lock detection and resilience
- Detailed error logging for debugging

### Data Structure
- Clipboard items stored as `ClipboardItem` objects
- Properties: text content, pinned status, custom name
- Automatic migration from older data formats

## Logging

All operations are logged to `clipman.log` with timestamps, including:
- Application startup/shutdown
- Clipboard item additions
- Pin/unpin operations
- Rename operations
- Search queries
- Error conditions

## Requirements

See `requirements.txt` for dependencies:
- tkinter (usually included with Python)
- pyperclip
- pygments (for syntax highlighting)

## Building

To create a standalone executable:

```powershell
.\build.ps1
```

The executable will be created in the `dist/clipman/` directory.