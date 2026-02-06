# File: /my-tkinter-app/src/gui/clipboard_manager.py

# TODO rip out all the explicit clipboard stuff and move it into a go cli/service that this will use instead.
import tkinter as tk
from tkinter import Listbox, Scrollbar, Button, Entry, Toplevel, PhotoImage, Text, messagebox
from tkinter.scrolledtext import ScrolledText
import pyperclip
import threading
import time
import pickle
import os
import json
import logging
# TODO create a script to install Linux dependencies for Linux
from pygments import highlight, styles
from pygments.lexers import JsonLexer, PythonLexer, CLexer
# TODO update this to support Linux as well
import winsound
#from pygments.formatters import Formatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('clipman.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClipboardItem:
    """Represents a single clipboard history item.
    
    Attributes:
        text: The clipboard text content.
        pinned: Whether the item is pinned to the top of the list.
        name: Optional custom name for the item.
    """
    
    def __init__(self, text, pinned=False, name=''):
        """Initialize a clipboard item.
        
        Args:
            text: The clipboard text content.
            pinned: Whether the item is pinned (default: False).
            name: Optional custom name for the item (default: '').
        """
        self.text = text
        self.pinned = pinned
        self.name = name
    
    def __eq__(self, other):
        """Compare items by text content.
        
        Args:
            other: Another ClipboardItem or string to compare.
            
        Returns:
            True if text content matches.
        """
        if isinstance(other, ClipboardItem):
            return self.text == other.text
        return self.text == other
    
    def __repr__(self):
        """String representation for debugging."""
        pin_status = "pinned" if self.pinned else "unpinned"
        name_part = f" ({self.name})" if self.name else ""
        return f"ClipboardItem({pin_status}{name_part}, {len(self.text)} chars)"


class TkFormatter():
    """Custom formatter for syntax highlighting in Tkinter text widgets.
    
    This formatter is designed to work with Pygments to apply syntax highlighting
    to text displayed in Tkinter widgets.
    """
    
    def __init__(self, text_widget, **options):
        """Initialize the formatter with a text widget.
        
        Args:
            text_widget: The Tkinter text widget to format.
            **options: Additional formatting options.
        """
        super().__init__(**options)
        self.text_widget = text_widget
        self.style = styles.get_style_by_name('default')

    def format(self, tokensource, outfile):
        """Format the token source for output.
        
        Args:
            tokensource: The source of syntax tokens to format.
            outfile: The output file or stream.
        """
        pass

class ClipboardManager:
    """Main application class for managing clipboard history.
    
    This class creates a GUI application that monitors the system clipboard,
    maintains a history of copied items, and allows users to search, view,
    restore, pin, and name clipboard items.
    
    Attributes:
        master: The root Tkinter window.
        clipboard_list: Full list of ClipboardItem objects.
        filtered_list: Filtered list based on search query.
        last_clipboard_data: The most recent clipboard content to avoid duplicates.
    """
    
    def __init__(self, master):
        """Initialize the clipboard manager with UI components and monitoring thread.
        
        Args:
            master: The root Tkinter window.
            
        Raises:
            RuntimeError: If the clipboard monitoring thread fails to start.
        """
        logger.info("Initializing ClipboardManager")
        self.master = master
        
        master.title("Clipman")
        master.geometry("800x600")  # Set the main window size to 800x600

        icon = PhotoImage(file="assets/clipboard.png")
        master.iconphoto(False, icon)
        logger.debug("UI components initialized")

        # Define colors
        self.bg_color = "#2e2e2e"
        self.entry_bg_color = "#3e3e3e"
        self.listbox_bg_color = "#3e3e3e"
        self.button_bg_color = "#4e4e4e"
        self.fg_color = "#ffffff"
        self.scrollbar_bg_color = "#4e4e4e"

        master.configure(bg=self.bg_color)

        # Clipboard list stores ClipboardItem objects
        self.clipboard_list = []
        self.filtered_list = []
        self.last_clipboard_data = ""

        self.search_bar = Entry(master, bg=self.entry_bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.search_bar.pack(side=tk.TOP, fill=tk.X)
        self.search_bar.bind("<KeyRelease>", self.filter_list)
        # TODO bind escape to clear search bar

        self.listbox = Listbox(master, bg=self.listbox_bg_color, fg=self.fg_color, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<Double-1>", self.open_item_in_new_window)
        self.listbox.bind("<Button-3>", self.show_context_menu)  # Right-click menu

        self.scrollbar = Scrollbar(master, orient="vertical", bg=self.scrollbar_bg_color)
        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.config(yscrollcommand=self.scrollbar.set)

        # Create context menu
        self.context_menu = tk.Menu(master, tearoff=0, bg=self.button_bg_color, fg=self.fg_color)
        self.context_menu.add_command(label="Pin/Unpin", command=self.toggle_pin)
        self.context_menu.add_command(label="Rename", command=self.rename_item)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Load to Clipboard", command=self.load_to_clipboard)
        self.context_menu.add_command(label="Remove", command=self.remove_from_clipboard)

        self.load_button = Button(master, text="Load to Clipboard", command=self.load_to_clipboard, bg=self.button_bg_color, fg=self.fg_color)
        self.load_button.pack(side=tk.BOTTOM, fill=tk.X)
        self.pin_button = Button(master, text="Pin/Unpin", command=self.toggle_pin, bg=self.button_bg_color, fg=self.fg_color)
        self.pin_button.pack(side=tk.BOTTOM, fill=tk.X)
        self.rename_button = Button(master, text="Rename", command=self.rename_item, bg=self.button_bg_color, fg=self.fg_color)
        self.rename_button.pack(side=tk.BOTTOM, fill=tk.X)
        self.remove_button = Button(master, text="Remove", command=self.remove_from_clipboard, bg=self.button_bg_color, fg=self.fg_color)
        self.remove_button.pack(side=tk.BOTTOM, fill=tk.X)

        self.load_clipboard_list()

        try:
            logger.info("Starting clipboard monitoring thread")
            self.update_clipboard_thread = threading.Thread(target=self.update_clipboard)
            self.update_clipboard_thread.daemon = True
            self.update_clipboard_thread.start()
            logger.info("Clipboard monitoring thread started successfully")
        except (RuntimeError, OSError) as e:
            logger.critical("Failed to start clipboard monitoring thread: %s", e, exc_info=True)
            self.on_closing()
            self.master.destroy()
            raise RuntimeError(f"Failed to start clipboard monitoring thread: {e}")

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_clipboard(self):
        """Continuously monitor the system clipboard for new content.
        
        This method runs in a background thread and polls the clipboard every 1-2 seconds.
        It handles clipboard access failures gracefully, such as when the screen is locked
        or another application is using the clipboard.
        
        The method will retry up to 60 times before giving up, allowing for temporary
        access issues like screen locks.
        """
        logger.info("Clipboard monitoring loop started")
        consecutive_failures = 0
        max_consecutive_failures = 60  # Allow for longer periods (e.g., screen locked)
        screen_locked_logged = False
        
        while True:
            try:
                clipboard_data = pyperclip.paste()
                
                # Reset failure tracking on success
                if consecutive_failures > 0:
                    if consecutive_failures >= 5:
                        logger.info("Clipboard access restored (screen may have been unlocked)")
                    consecutive_failures = 0
                    screen_locked_logged = False
                
                # Check if clipboard data already exists
                already_in_list = any(
                    item.text == clipboard_data for item in self.clipboard_list
                ) or clipboard_data == self.last_clipboard_data
                
                if not already_in_list and not clipboard_data == "":
                    logger.debug("New clipboard item detected (length: %s chars)", len(clipboard_data))
                    new_item = ClipboardItem(clipboard_data)
                    self.clipboard_list.append(new_item)
                    self.refresh_display()
                    self.last_clipboard_data = clipboard_data
                    logger.info("Added new clipboard item. Total items: %s", len(self.clipboard_list))

                time.sleep(1)
                
            except pyperclip.PyperclipWindowsException:
                # Clipboard access blocked - common when screen is locked or another app is using clipboard
                consecutive_failures += 1
                
                # Log only once when we suspect screen is locked to avoid log spam
                if consecutive_failures == 5 and not screen_locked_logged:
                    logger.info("Clipboard access blocked (screen may be locked or clipboard in use by another app)")
                    screen_locked_logged = True
                elif consecutive_failures < 5:
                    logger.debug("Clipboard temporarily blocked, will retry (attempt %s)", consecutive_failures)
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Clipboard access failed %s times consecutively, giving up", max_consecutive_failures, exc_info=True)
                    self.on_closing()
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    messagebox.showerror("Error", f"Unable to access clipboard after {max_consecutive_failures} attempts.")
                    self.master.destroy()
                    break
                
                # Use consistent polling interval instead of exponential backoff
                # Screen lock can last a long time, so we just keep checking
                time.sleep(2)
                
            except (OSError, RuntimeError) as e:
                # These are more serious errors
                logger.error("Critical error in clipboard monitoring loop: %s", e, exc_info=True)
                self.on_closing()
                winsound.MessageBeep(winsound.MB_ICONHAND)
                messagebox.showerror("Error", f"Critical error in clipboard monitoring: {e}")
                self.master.destroy()
                break 

    def load_to_clipboard(self):
        """Load the currently selected item back to the system clipboard.
        
        If an item is selected in the listbox, this copies it to the system clipboard.
        Logs a warning if no item is selected.
        """
        selected_index = self.listbox.curselection()
        if selected_index:
            idx = selected_index[0]
            item = self.filtered_list[idx]
            pyperclip.copy(item.text)
            logger.info("Loaded item to clipboard (length: %s chars)", len(item.text))
        else:
            logger.warning("Load to clipboard requested but no item selected")

    def remove_from_clipboard(self):
        """Remove selected items from the clipboard history.
        
        Removes all selected items from both the clipboard_list and filtered_list,
        updates the UI listbox, and clears the system clipboard. Logs a warning
        if no items are selected.
        """
        selected_indices = self.listbox.curselection()
        if selected_indices:
            removed_count = len(selected_indices)
            logger.info("Removing %s item(s) from clipboard history", removed_count)
            items_to_remove = [self.filtered_list[i] for i in selected_indices]
            for item in items_to_remove:
                if item in self.clipboard_list:
                    self.clipboard_list.remove(item)
                if item in self.filtered_list:
                    self.filtered_list.remove(item)
            self.refresh_display()
            self.last_clipboard_data = ""
            pyperclip.copy("")  # clear out the clipboard
            logger.info("Removed %s item(s). Total items remaining: %s", removed_count, len(self.clipboard_list))
        else:
            logger.warning("Remove requested but no items selected")

    def filter_list(self, event):
        """Filter the clipboard history based on the search bar input.
        
        Called whenever the search bar content changes. Performs case-insensitive
        substring matching and updates the listbox to show only matching items.
        
        Args:
            event: The Tkinter key release event that triggered this method.
        """
        search_query = self.search_bar.get().lower()
        self.filtered_list = [
            item for item in self.clipboard_list 
            if search_query in item.text.lower() or search_query in item.name.lower()
        ]
        self.refresh_display()
        logger.debug("Filter applied: '%s' - %s items match", search_query, len(self.filtered_list))

    def load_clipboard_list(self):
        """Load clipboard history from disk on application startup.
        
        Attempts to load the clipboard history from 'clipboard_data.pkl' if it exists.
        If loading fails due to corruption or other errors, starts with an empty list.
        Supports migration from old string format to new dict format.
        Logs the result of the operation.
        """
        if os.path.exists("clipboard_data.pkl"):
            try:
                logger.info("Loading clipboard history from file")
                with open("clipboard_data.pkl", "rb") as f:
                    loaded_data = pickle.load(f)
                    
                    # Migrate old formats to ClipboardItem objects
                    if loaded_data:
                        if isinstance(loaded_data[0], str):
                            # Old format: list of strings
                            logger.info("Migrating old string format to ClipboardItem format")
                            self.clipboard_list = [ClipboardItem(item) for item in loaded_data]
                        elif isinstance(loaded_data[0], dict):
                            # Dict format: convert to ClipboardItem
                            logger.info("Migrating dict format to ClipboardItem format")
                            self.clipboard_list = [
                                ClipboardItem(item['text'], item['pinned'], item['name'])
                                for item in loaded_data
                            ]
                        else:
                            # Already ClipboardItem objects
                            self.clipboard_list = loaded_data
                    else:
                        self.clipboard_list = []
                    
                    self.filtered_list = self.clipboard_list.copy()
                    self.refresh_display()
                
                pinned_count = sum(1 for item in self.clipboard_list if item.pinned)
                logger.info("Loaded %s items from clipboard history (%s pinned)", len(self.clipboard_list), pinned_count)
            except (pickle.PickleError, OSError) as e:
                logger.error("Failed to load clipboard history: %s", e, exc_info=True)
                self.clipboard_list = []
                self.filtered_list = []
        else:
            logger.info("No existing clipboard history found, starting fresh")

    def save_clipboard_list(self):
        """Save the current clipboard history to disk.
        
        Persists the clipboard_list to 'clipboard_data.pkl' using pickle serialization.
        Logs success or failure of the operation.
        """
        try:
            pinned_count = sum(1 for item in self.clipboard_list if item.pinned)
            logger.info("Saving clipboard history (%s items, %s pinned)", len(self.clipboard_list), pinned_count)
            with open("clipboard_data.pkl", "wb") as f:
                pickle.dump(self.clipboard_list, f)
            logger.info("Clipboard history saved successfully")
        except (pickle.PickleError, OSError) as e:
            logger.error("Failed to save clipboard history: %s", e, exc_info=True)

    def on_closing(self):
        """Handle application shutdown.
        
        Called when the user closes the main window. Saves the clipboard history
        to disk and destroys the window gracefully.
        """
        logger.info("Application closing, saving clipboard history")
        self.save_clipboard_list()
        self.master.destroy()
        logger.info("ClipboardManager shutdown complete")

    def open_item_in_new_window(self, event):
        """Open the selected clipboard item in a new window for detailed viewing.
        
        Creates a new window with a scrollable text widget displaying the selected item.
        If the content is valid JSON, it will be pretty-printed with indentation.
        Includes a button to copy the item back to the clipboard.
        
        Args:
            event: The Tkinter double-click event that triggered this method.
        """
        selected_index = self.listbox.curselection()
        if selected_index:
            idx = selected_index[0]
            item = self.filtered_list[idx]
            selected_text = item.text
            item_name = item.name if item.name else "Clipboard Item"
            
            logger.info("Opening item in new window (length: %s chars)", len(selected_text))
            new_window = Toplevel(self.master)
            new_window.title(item_name)
            text_widget = ScrolledText(new_window, wrap=tk.WORD, background=self.bg_color, foreground=self.fg_color)
            try:
                json_data = json.loads(selected_text)
                pretty_json = json.dumps(json_data, indent=4)
                text_widget.insert(tk.END, pretty_json)
                logger.debug("Displayed item as formatted JSON")
            except json.JSONDecodeError:
                text_widget.insert(tk.END, selected_text)
                logger.debug("Displayed item as plain text")

            text_widget.pack(fill=tk.BOTH, expand=True)

            load_button = Button(new_window, text="Load to Clipboard", command=lambda: pyperclip.copy(selected_text), bg=self.button_bg_color, fg=self.fg_color)
            load_button.pack(side=tk.BOTTOM, fill=tk.X)


            #lexer = self.detect_lexer(selected_text)

            #if lexer == None:
            #    text_widget.insert(tk.END, selected_text)
            # else:
            #     highlighted_content = highlight(selected_text, lexer, TkFormatter(text_widget))
            #     text_widget.insert(tk.END, highlighted_content)

    def show_context_menu(self, event):
        """Display the context menu on right-click.
        
        Args:
            event: The Tkinter mouse button event.
        """
        try:
            # Select the item under the cursor
            index = self.listbox.nearest(event.y)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            
            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_pin(self):
        """Toggle the pinned status of the selected item.
        
        Pinned items appear at the top of the list with a pin indicator.
        """
        selected_index = self.listbox.curselection()
        if selected_index:
            idx = selected_index[0]
            item = self.filtered_list[idx]
            item.pinned = not item.pinned
            status = "pinned" if item.pinned else "unpinned"
            item_preview = item.text[:50].replace('\n', ' ')
            logger.info("Item %s: %s", status, item_preview)
            self.refresh_display()
            # Auto-save after pinning to ensure persistence
            self.save_clipboard_list()
        else:
            logger.warning("Toggle pin requested but no item selected")

    def rename_item(self):
        """Prompt the user to rename the selected clipboard item.
        
        Opens a dialog to enter a custom name for the item.
        """
        selected_index = self.listbox.curselection()
        if selected_index:
            idx = selected_index[0]
            item = self.filtered_list[idx]
            
            # Create a simple dialog for renaming
            dialog = Toplevel(self.master)
            dialog.title("Rename Item")
            dialog.geometry("400x150")
            dialog.configure(bg=self.bg_color)
            
            label = tk.Label(dialog, text="Enter a name for this item:", bg=self.bg_color, fg=self.fg_color)
            label.pack(pady=10)
            
            entry = Entry(dialog, bg=self.entry_bg_color, fg=self.fg_color, insertbackground=self.fg_color, width=50)
            entry.insert(0, item.name)
            entry.pack(pady=5)
            entry.focus()
            
            def save_name():
                new_name = entry.get().strip()
                item.name = new_name
                logger.info("Item renamed to: '%s'", new_name if new_name else "(unnamed)")
                self.refresh_display()
                # Auto-save after renaming to ensure persistence
                self.save_clipboard_list()
                dialog.destroy()
            
            def cancel():
                dialog.destroy()
            
            entry.bind("<Return>", lambda e: save_name())
            entry.bind("<Escape>", lambda e: cancel())
            
            button_frame = tk.Frame(dialog, bg=self.bg_color)
            button_frame.pack(pady=10)
            
            save_btn = Button(button_frame, text="Save", command=save_name, bg=self.button_bg_color, fg=self.fg_color, width=10)
            save_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = Button(button_frame, text="Cancel", command=cancel, bg=self.button_bg_color, fg=self.fg_color, width=10)
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
            # Make dialog modal
            dialog.transient(self.master)
            dialog.grab_set()
        else:
            logger.warning("Rename requested but no item selected")

    def refresh_display(self):
        """Refresh the listbox display with current filtered list.
        
        Sorts items to show pinned items first, then displays them with
        appropriate formatting including pin indicators and custom names.
        """
        # Sort: pinned items first, then unpinned
        sorted_list = sorted(self.filtered_list, key=lambda x: (not x.pinned, self.filtered_list.index(x)))
        self.filtered_list = sorted_list
        
        # Clear and repopulate listbox
        self.listbox.delete(0, tk.END)
        for item in self.filtered_list:
            display_text = self._format_display_text(item)
            self.listbox.insert(tk.END, display_text)

    def _format_display_text(self, item):
        """Format an item for display in the listbox.
        
        Args:
            item: ClipboardItem object.
            
        Returns:
            Formatted string for display.
        """
        pin_indicator = "📌 " if item.pinned else ""
        name_part = f"[{item.name}] " if item.name else ""
        # Truncate long text for display
        text_preview = item.text.replace('\n', ' ')[:100]
        if len(item.text) > 100:
            text_preview += "..."
        return f"{pin_indicator}{name_part}{text_preview}"

    def detect_lexer(self, text):
        """Detect the appropriate syntax highlighter for the given text.
        
        Attempts to determine the programming language or format of the text
        to select an appropriate Pygments lexer for syntax highlighting.
        
        Args:
            text: The text content to analyze.
            
        Returns:
            A Pygments lexer instance (JsonLexer, CLexer, or PythonLexer),
            or None if the content type cannot be determined.
        """
        try:
            json.loads(text)
            return JsonLexer()
        except json.JSONDecodeError:
            pass

        if text.strip().startswith("using ") or text.strip().startswith("namespace "):
            return CLexer()

        if text.strip().startswith("def ") or text.strip().startswith("class "):
            return PythonLexer()

        return None  # Default to plain text

def main():
    """Application entry point.
    
    Initializes the Tkinter root window, creates the ClipboardManager instance,
    and starts the main event loop. Logs application startup, readiness, and
    termination events.
    
    Raises:
        Exception: Any unhandled exception is logged and re-raised.
    """
    logger.info("Starting Clipman application")
    try:
        root = tk.Tk()
        clipboard_manager = ClipboardManager(root)
        logger.info("Application ready")
        root.mainloop()
    except Exception as e:
        logger.critical("Unhandled exception in main: %s", e, exc_info=True)
        raise
    finally:
        logger.info("Application terminated")

if __name__ == "__main__":
    main()
