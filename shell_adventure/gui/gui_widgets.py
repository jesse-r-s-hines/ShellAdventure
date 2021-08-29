import re, webbrowser
import tkinter as tk
from tkinter import ttk, font
from tkinter import filedialog

class WrappingLabel(ttk.Label):
    """Label that automatically adjusts the wrap to the size"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, borderwidth = 0, **kwargs) # borderwidth = 0 fixes "chopping off" of pieces of letters at the edges
        self.bind('<Configure>', lambda e: self.config(wraplength = e.width))

class SelectableMessage(tk.Text):
    """ Displays multiline selectable text. Also allows markdown style hyperlinks. """
    # see https://stackoverflow.com/a/20567348/14172697 and
    # https://stackoverflow.com/questions/52722821/how-to-be-able-to-select-the-text-in-a-tkinter-message-widget

    def __init__(self, master, text: str = "", *args, **kwargs):
        defaults = dict(
            borderwidth = 0,
            highlightthickness = 0,
            wrap = tk.WORD,
            bg = master.cget('bg'),
            font = font.Font(font = 'TkDefaultFont'),
        )
        kwargs = {**defaults, **kwargs }
        super().__init__(master, *args, **kwargs)

        hyperlinks, text = self._extract_links(text)
        self.insert(tk.INSERT, text)
        for (start, end, link) in hyperlinks:
            self.tag_add('link', start, end)
            self.tag_add(f'url:{link}', start, end)

        self.tag_config('link', underline = True, foreground = 'blue')
        self.tag_bind('link', "<Button-1>", self._open_link)

        self.bind("<1>", lambda event: self.focus_set()) # Hack to allow copying from DISABLED textbox
        self.bind("<Configure>", self.update_size)
        self.configure(state = tk.DISABLED) # Have to disable after inserting text

    def _extract_links(self, text: str):
        """ Extract markdown style links into a list of (start_index, end_index, link) tuples, and display text """
        pattern = r"\[(.*?)\]\((.*?)\)" # match [text](www.example.com)
        hyperlinks = []

        # Go through the text,
        offset = 0 # Number of chars the new text will be shorter than the old
        for match in re.finditer(pattern, text):
            start = match.start() - offset
            display, link = match.groups()
            hyperlinks.append( (f"1.0+{start}c", f"1.0+{start + len(display)}c", link) )
            offset += (len(match[0]) - len(display))

        new_text = re.sub(pattern, r'\1', text)

        return hyperlinks, new_text

    def _open_link(self, event):
        tags = self.tag_names(tk.CURRENT)
        url = next(filter(lambda s: s.startswith("url:"), tags))[4:]
        webbrowser.open(url)

    def update_size(self, event = None):
        lines = self.count("1.0", "end", "update", "displaylines") # gets lines after wordwrap
        self.config(height = lines)

def popup_box(title: str, text: str):
    popup = tk.Toplevel()
    popup.title(title)

    message = SelectableMessage(popup, text)
    message.pack(side = tk.TOP, padx = 10, pady = 10, fill = tk.BOTH, expand = True)

    close_button = tk.Button(popup, text="OK", command = popup.destroy)
    close_button.pack(side = tk.BOTTOM)

def standalone_fileselect(**options):
    """ Creates a standalone tk window that shows a fileselect and returns the file. """
    root = tk.Tk()
    root.withdraw()
    result = filedialog.askopenfilename(**options)
    root.destroy()
    return result
