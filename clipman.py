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


class TkFormatter():
    def __init__(self, text_widget, **options):
        super().__init__(**options)
        self.text_widget = text_widget
        self.style = styles.get_style_by_name('default')

    def format(self, tokensource, outfile):
        pass

class ClipboardManager:
    def __init__(self, master):
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

        self.scrollbar = Scrollbar(master, orient="vertical", bg=self.scrollbar_bg_color)
        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.config(yscrollcommand=self.scrollbar.set)

        self.load_button = Button(master, text="Load to Clipboard", command=self.load_to_clipboard, bg=self.button_bg_color, fg=self.fg_color)
        self.load_button.pack(side=tk.BOTTOM, fill=tk.X)
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
            logger.critical(f"Failed to start clipboard monitoring thread: {e}", exc_info=True)
            self.on_closing()
            self.master.destroy()
            raise RuntimeError(f"Failed to start clipboard monitoring thread: {e}")

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_clipboard(self):
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
                
                already_in_list = (
                    self.clipboard_list.__contains__(clipboard_data)
                    or self.filtered_list.__contains__(clipboard_data)
                    or clipboard_data == self.last_clipboard_data
                )
                if not already_in_list and not clipboard_data == "":
                    logger.debug(f"New clipboard item detected (length: {len(clipboard_data)} chars)")
                    self.clipboard_list.append(clipboard_data)
                    self.filtered_list.append(clipboard_data)
                    self.listbox.insert(tk.END, clipboard_data)
                    self.last_clipboard_data = clipboard_data
                    logger.info(f"Added new clipboard item. Total items: {len(self.clipboard_list)}")

                time.sleep(1)
                
            except pyperclip.PyperclipWindowsException as e:
                # Clipboard access blocked - common when screen is locked or another app is using clipboard
                consecutive_failures += 1
                
                # Log only once when we suspect screen is locked to avoid log spam
                if consecutive_failures == 5 and not screen_locked_logged:
                    logger.info("Clipboard access blocked (screen may be locked or clipboard in use by another app)")
                    screen_locked_logged = True
                elif consecutive_failures < 5:
                    logger.debug(f"Clipboard temporarily blocked, will retry (attempt {consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Clipboard access failed {max_consecutive_failures} times consecutively, giving up", exc_info=True)
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
                logger.error(f"Critical error in clipboard monitoring loop: {e}", exc_info=True)
                self.on_closing()
                winsound.MessageBeep(winsound.MB_ICONHAND)
                messagebox.showerror("Error", f"Critical error in clipboard monitoring: {e}")
                self.master.destroy()
                break 

    def load_to_clipboard(self):
        selected_index = self.listbox.curselection()
        if selected_index:
            selected_text = self.listbox.get(selected_index)
            pyperclip.copy(selected_text)
            logger.info(f"Loaded item to clipboard (length: {len(selected_text)} chars)")
        else:
            logger.warning("Load to clipboard requested but no item selected")

    def remove_from_clipboard(self):
        selected_indices = self.listbox.curselection()
        if selected_indices:
            removed_count = len(selected_indices)
            logger.info(f"Removing {removed_count} item(s) from clipboard history")
            for i in reversed(selected_indices):
                selected_text = self.listbox.get(i)
                self.clipboard_list.remove(selected_text)
                self.filtered_list.remove(selected_text)
                self.listbox.delete(i)
            self.last_clipboard_data = ""
            pyperclip.copy("") # clear out the clipboard
            logger.info(f"Removed {removed_count} item(s). Total items remaining: {len(self.clipboard_list)}")
        else:
            logger.warning("Remove requested but no items selected")

    def filter_list(self, event):
        search_query = self.search_bar.get().lower()
        self.listbox.delete(0, tk.END)
        self.filtered_list = [item for item in self.clipboard_list if search_query in item.lower()]
        for item in self.filtered_list:
            self.listbox.insert(tk.END, item)
        logger.debug(f"Filter applied: '{search_query}' - {len(self.filtered_list)} items match")

    def load_clipboard_list(self):
        if os.path.exists("clipboard_data.pkl"):
            try:
                logger.info("Loading clipboard history from file")
                with open("clipboard_data.pkl", "rb") as f:
                    self.clipboard_list = pickle.load(f)
                    self.filtered_list = self.clipboard_list.copy()
                    for item in self.clipboard_list:
                        self.listbox.insert(tk.END, item)
                logger.info(f"Loaded {len(self.clipboard_list)} items from clipboard history")
            except (pickle.PickleError, OSError) as e:
                logger.error(f"Failed to load clipboard history: {e}", exc_info=True)
                self.clipboard_list = []
                self.filtered_list = []
        else:
            logger.info("No existing clipboard history found, starting fresh")

    def save_clipboard_list(self):
        try:
            logger.info(f"Saving clipboard history ({len(self.clipboard_list)} items)")
            with open("clipboard_data.pkl", "wb") as f:
                pickle.dump(self.clipboard_list, f)
            logger.info("Clipboard history saved successfully")
        except (pickle.PickleError, OSError) as e:
            logger.error(f"Failed to save clipboard history: {e}", exc_info=True)

    def on_closing(self):
        logger.info("Application closing, saving clipboard history")
        self.save_clipboard_list()
        self.master.destroy()
        logger.info("ClipboardManager shutdown complete")

    def open_item_in_new_window(self, event):
        selected_index = self.listbox.curselection()
        if selected_index:
            selected_text = self.listbox.get(selected_index)
            logger.info(f"Opening item in new window (length: {len(selected_text)} chars)")
            new_window = Toplevel(self.master)
            new_window.title("Clipboard Item")
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

    def detect_lexer(self, text):
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
    logger.info("Starting Clipman application")
    try:
        root = tk.Tk()
        clipboard_manager = ClipboardManager(root)
        logger.info("Application ready")
        root.mainloop()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        raise
    finally:
        logger.info("Application terminated")

if __name__ == "__main__":
    main()
