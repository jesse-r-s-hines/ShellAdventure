from typing import List, Tuple, Dict, ClassVar
from pathlib import PurePosixPath
import tkinter as tk
from tkinter import StringVar, ttk, font, messagebox
import tkinter.simpledialog as simpledialog
from tkinter.scrolledtext import ScrolledText
from ttkthemes import ThemedTk
import traceback
from PIL import ImageTk, Image
from .scrolled_frame import VerticalScrolledFrame
from . import tutorial
from .support import Puzzle, PKG
class WrappingLabel(ttk.Label):
    """Label that automatically adjusts the wrap to the size"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, borderwidth = 0, **kwargs) # borderwidth = 0 fixes "chopping off" of pieces of letters at the edges
        self.bind('<Configure>', lambda e: self.config(wraplength = e.width))

class GUI(ThemedTk):
    def __init__(self, tutorial: tutorial.Tutorial):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        super().__init__(theme="radiance")

        self.tutorial = tutorial
        self.student_cwd: PurePosixPath = None # The path to the student's current directory
        self.file_tree_root = PurePosixPath("/") # The root of the displayed file tree

        self.file_tree: ttk.Treeview = None
        self.file_icons = self.get_file_icons()

        self.time_label = StringVar(self, value = "Time: 00:00")
        self.score_label = StringVar(self, value = "Score: 0/10")
        # self.flag_input = StringVar(self, value="")

        self.title("Shell Adventure")
        self.minsize(300, 100) # To keep you from being able to shrink everything off the screen.
        self.columnconfigure(0, weight = 1, minsize = 80)
        self.rowconfigure(0, weight = 1, minsize = 80)

        status_bar = self.make_status_bar(self)
        status_bar.pack(side = tk.TOP, fill = tk.X, expand = False)

        self.file_tree = self.make_file_tree(self)
        self.file_tree.pack(side = tk.TOP, fill = tk.BOTH, expand = True)

        self.puzzle_frame = self.make_puzzle_frame(self)
        self.puzzle_frame.pack(side = tk.BOTTOM, fill = tk.BOTH, expand = True)
        self.update_puzzle_frame()

        def update_loop(): # TODO make this trigger after every command instead of on a loop
            self.update_gui()
            self.after(250, update_loop)
        update_loop()

        self.start_timer_loop()

        if self.student_cwd != self.file_tree_root: # can't really display pointer to root.
            self.file_tree.see(str(self.student_cwd)) # type: ignore # open all parents and scroll to (parents should already be open)

        # for file in [*self.student_cwd.parents, self.student_cwd]:
        #     self.file_tree.item(str(file), open = True) # open it
        #     self.load_folder(str(file_id), open_new = file_was_open or open_new) # trigger update on the subfolder

        self.mainloop()

    def get_file_icons(self) -> Dict[Tuple[bool, bool], ImageTk.PhotoImage]:
        """ Returns a map of icons representing 4 file types. Maps (is_dir, is_symlink) tuples to the icons """
        icon_files = { 
            (False, False): "file.png",
            (False, True ): "file_symlink.png",
            (True,  False): "folder.png",
            (True,  True ): "folder_symlink.png",
        }
        # fetch icons files. We have to save to a field or tkinter will lose the images somehow.
        file_icons = {}
        for key, file in icon_files.items():
            img = Image.open(PKG / "icons" / file).resize((16, 16), Image.ANTIALIAS)
            file_icons[key] = ImageTk.PhotoImage(img)
        return file_icons

    def make_status_bar(self, master):
        """ Returns the status bar that displays time and current score. """
        status_bar = ttk.Frame(master)

        ttk.Label(status_bar, textvariable = self.score_label).pack(side = tk.RIGHT, padx = 5) # Score: 0/10
        ttk.Separator(status_bar, orient='vertical').pack(side = tk.RIGHT, fill = tk.Y, padx = 5)
        ttk.Label(status_bar, textvariable = self.time_label).pack(side = tk.RIGHT) # Time: 01:5
        ttk.Separator(status_bar, orient='vertical').pack(side = tk.RIGHT, fill = tk.Y, padx = 5)
        
        return status_bar

    def start_timer_loop(self):
        """ Starts a loop which will update the timer every second. """
        self.after(1000, self.start_timer_loop)

        time = self.tutorial.time()
        hours, remainder = divmod(int(time.total_seconds()), 60 * 60)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            self.time_label.set(f"Time: {hours}:{minutes:02}:{seconds:02}")
        else:
            self.time_label.set(f"Time: {minutes:02}:{seconds:02}")

    def make_file_tree(self, master):
        """ Returns the file view """
        file_tree = ttk.Treeview(master, show="tree") # don't show the heading

        file_tree.tag_configure("cwd", font = font.Font(weight="bold"))

        def on_open(e):
            item = file_tree.focus()
            if not file_tree.tag_has("loaded", item):
                self.load_folder(item)

        file_tree.tag_bind("dir", "<<TreeviewOpen>>", on_open)

        return file_tree

    def make_puzzle_frame(self, master) -> VerticalScrolledFrame:
        """ Returns a frame container the puzzle list. """
        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        puzzle_frame = VerticalScrolledFrame(master)
        puzzle_frame.interior.columnconfigure(0, weight = 1)
        puzzle_frame.interior.rowconfigure(0, weight = 1)

        return puzzle_frame

    def update_puzzle_frame(self):
        """ Remakes the puzzle list. """
        for widget in self.puzzle_frame.interior.winfo_children(): # Should only contain one element
            widget.destroy()

        frame = ttk.LabelFrame(self.puzzle_frame.interior, text = 'Puzzles:')
        frame.grid(column = 0, row = 0, sticky = 'WENS')
        frame.columnconfigure(0, weight = 1)

        for i, puzzle in enumerate(self.tutorial.get_current_puzzles()):
            label = WrappingLabel(frame, text = f"{i+1}. {puzzle.question}", wraplength=50)
            label.grid(row = i, column = 0, padx = 5, pady = 5, sticky="EWNS")

            button = ttk.Button(frame,
                text = "Solved" if puzzle.solved else "Solve",
                command = lambda p=puzzle: self.solve_puzzle(p), # type: ignore
                state = "disabled" if puzzle.solved else "enabled"
            )
            button.bind('<Return>', lambda e, p=puzzle: self.solve_puzzle(p)) # type: ignore
            button.grid(row = i, column = 1, padx = 5, sticky="S")

    def _add_tree_tag(self, iid, tag):
        """ Adds a tag to the given item in the Treeview. """
        old_tags = list(self.file_tree.item(iid, option = "tags"))
        self.file_tree.item(iid, tags = old_tags + [tag])

    def load_folder(self, folder: str, was_open: bool = False):
        """
        Updates the given folder in the file tree. Indicates the student_cwd if it is under folder, and opens it.
        Pass the iid of the node which is the path to the file except that "" is the root.
        If was_open is True, new folders will be opened, otherwise all subfolders except cwd will start closed.
        """
        self._add_tree_tag(folder, "loaded")

        # get old_files as dict of {path: is_open,...}
        old_files = self.file_tree.get_children(folder)
        old_files = {file: self.file_tree.item(file, option = "open") for file in old_files}

        # get new children, convert "" to the folder that is the root of the file tree
        new_files = self.tutorial.get_files(PurePosixPath(folder if folder else self.file_tree_root))
        new_files.sort()
       
        # Update the Treeview
        for i, (is_dir, is_symlink, file) in enumerate(new_files):
            file_id = str(file) # Use full path as iid
            file_text = file.name # The text to display for the file
            file_icon = self.file_icons[(is_dir, is_symlink)]
            file_in_tree = file_id in old_files
            file_was_open = old_files.pop(file_id, False) # We want to keep open folders that were already open

            tags = ["dir"] if is_dir else ["file"]
            if is_symlink: tags.append("symlink")
            if self.student_cwd == file:
                tags.append("cwd")
                file_text += " 🠔"
            
            if file_in_tree:
                self.file_tree.item(file, text = file_text, tags = tags, image = file_icon) # modify existing item.
                self.file_tree.move(file, folder, i)
                # Leave existing children. The will be modified when thw file is opened since the file is no longer tagged as loaded
            else:
                self.file_tree.insert(folder, i, iid = file_id, text = file_text, tags = tags, image = file_icon)

            if is_dir:
                # If a directory is new, or was already open, open it. Don't open symlinks (to avoid infinite recursion)
                # Also open the current directory (and any parents of it)
                is_in_cwd_path = (file == self.student_cwd or file in self.student_cwd.parents)
                should_open = file_was_open or is_in_cwd_path or (was_open and not file_in_tree and not is_symlink)
                if should_open: 
                    self.file_tree.item(file_id, open = True) # open it
                    self.load_folder(file_id, was_open = file_was_open) # trigger update on the subfolder
                elif not file_in_tree:
                    self.file_tree.insert(file, tk.END, tags = ["dummy"]) # insert a dummy child so that is shows as "openable"
            else:
                # if a folder has been converted into a file, we'd need to delete the children under it.
                self.file_tree.delete(*self.file_tree.get_children(file))

        # Delete any files from the tree that no longer exist
        for file in old_files.keys():
            self.file_tree.delete(file)

        if len(new_files) == 0:
            self.file_tree.insert(folder, tk.END, tags = ["dummy"]) # insert a dummy child so that is shows as "openable"

    def update_gui(self):
        """ Updates the file tree, score, etc to match the current state of the tutorial. """
        self.student_cwd = self.tutorial.get_student_cwd()
        self.load_folder("")

        self.score_label.set(f"Score: {self.tutorial.current_score()}/{self.tutorial.total_score()}")

    def solve_puzzle(self, puzzle: Puzzle):
        flag = None
        if "flag" in puzzle.checker_args:
            flag = simpledialog.askstring("Input", puzzle.question, parent = self)

        solved, feedback = self.tutorial.solve_puzzle(puzzle, flag)
        messagebox.showinfo("Feedback", feedback)

        if solved:
            self.update_puzzle_frame()
            if self.tutorial.is_finished(): # then quit the tutorial
                self.destroy()

    def report_callback_exception(self, exc, val, tb):
        """ Override. """
        self.destroy()
        # Raising the exception so that we can handle it in the launch script 
        raise val from None # none so we don't get "while handling..."
