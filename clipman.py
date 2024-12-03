# File: /my-tkinter-app/src/gui/clipboard_manager.py

import tkinter as tk
from tkinter import Listbox, Scrollbar, Button, Entry, Toplevel, PhotoImage, Text, messagebox
from tkinter.scrolledtext import ScrolledText
import pyperclip
import threading
import time
import pickle
import os
import json
# TODO create a script to install Linux dependencies for Linux
from pygments import highlight, styles
from pygments.lexers import JsonLexer, PythonLexer, CLexer
# TODO update this to support Linux as well
import winsound
#from pygments.formatters import Formatter

class TkFormatter():
    def __init__(self, text_widget, **options):
        super().__init__(**options)
        self.text_widget = text_widget
        self.style = styles.get_style_by_name('default')

    def format(self, tokensource, outfile):
        pass

class ClipboardManager:
    def __init__(self, master):
        self.master = master
        
        master.title("Clipman")
        master.geometry("800x600")  # Set the main window size to 800x600

        icon = PhotoImage(file="assets/clipboard.png")
        master.iconphoto(False, icon)

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
            self.update_clipboard_thread = threading.Thread(target=self.update_clipboard)
            self.update_clipboard_thread.daemon = True
            self.update_clipboard_thread.start()
        except Exception as e:
            self.master.destroy()
            main()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_clipboard(self):
        try:
            while True:
                clipboard_data = pyperclip.paste()
                
                already_in_list = (
                    self.clipboard_list.__contains__(clipboard_data)
                    or self.filtered_list.__contains__(clipboard_data)
                    or clipboard_data == self.last_clipboard_data
                )
                if not already_in_list and not clipboard_data == "":
                    self.clipboard_list.append(clipboard_data)
                    self.filtered_list.append(clipboard_data)
                    self.listbox.insert(tk.END, clipboard_data)
                    self.last_clipboard_data = clipboard_data

                time.sleep(1)
        except Exception as e:
            winsound.MessageBeep(winsound.MB_ICONHAND)  # Play error sound
            messagebox.showerror("Error", f"Error in clipboard_manager: {e}")
            self.master.destroy()
            main() 

    def load_to_clipboard(self):
        selected_index = self.listbox.curselection()
        if selected_index:
            selected_text = self.listbox.get(selected_index)
            pyperclip.copy(selected_text)

    def remove_from_clipboard(self):
        selected_indices = self.listbox.curselection()
        if selected_indices:
            for i in reversed(selected_indices):
                selected_text = self.listbox.get(i)
                self.clipboard_list.remove(selected_text)
                self.filtered_list.remove(selected_text)
                self.listbox.delete(i)
            self.last_clipboard_data = ""
            pyperclip.copy("") # clear out the clipboard

    def filter_list(self, event):
        search_query = self.search_bar.get().lower()
        self.listbox.delete(0, tk.END)
        self.filtered_list = [item for item in self.clipboard_list if search_query in item.lower()]
        for item in self.filtered_list:
            self.listbox.insert(tk.END, item)

    def load_clipboard_list(self):
        if os.path.exists("clipboard_data.pkl"):
            with open("clipboard_data.pkl", "rb") as f:
                self.clipboard_list = pickle.load(f)
                self.filtered_list = self.clipboard_list.copy()
                for item in self.clipboard_list:
                    self.listbox.insert(tk.END, item)

    def save_clipboard_list(self):
        with open("clipboard_data.pkl", "wb") as f:
            pickle.dump(self.clipboard_list, f)

    def on_closing(self):
        self.save_clipboard_list()
        self.master.destroy()

    def open_item_in_new_window(self, event):
        selected_index = self.listbox.curselection()
        if selected_index:
            selected_text = self.listbox.get(selected_index)
            new_window = Toplevel(self.master)
            new_window.title("Clipboard Item")
            text_widget = ScrolledText(new_window, wrap=tk.WORD, background=self.bg_color, foreground=self.fg_color)
            try:
                json_data = json.loads(selected_text)
                pretty_json = json.dumps(json_data, indent=4)
                text_widget.insert(tk.END, pretty_json)
            except json.JSONDecodeError:
                text_widget.insert(tk.END, selected_text)

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
    root = tk.Tk()
    clipboard_manager = ClipboardManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()