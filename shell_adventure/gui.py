from typing import List, Tuple, Dict
from . import tutorial
from .support import Puzzle, PathLike
from pathlib import PurePosixPath
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
import tkinter.messagebox
from .scrolled_frame import VerticalScrolledFrame

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
        # self.flagInput = StringVar(self, value="")

        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        self.puzzles: Dict[Puzzle, Tuple[WrappingLabel, ttk.Button]] = {}
        self.file_tree: ttk.Treeview = None

        self.title("Shell Adventure")
        self.minsize(300, 100) # To keep you from being able to shrink everything off the screen.
        self.columnconfigure(0, weight = 1, minsize = 80)
        self.rowconfigure(0, weight = 1, minsize = 80)

        puzzle_frame = self.make_puzzle_frame(self)
        puzzle_frame.pack(side = tk.BOTTOM, fill = tk.BOTH, expand = True)

        file_tree = self.make_file_tree(self)
        file_tree.pack(side = tk.TOP, fill = tk.BOTH, expand = True)

        self.mainloop()

    def make_puzzle_frame(self, master):
        """ Returns a frame container the puzzle list. Stores the labels and buttons in the frame in self.puzzles """
        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        scrollable = VerticalScrolledFrame(master)
        scrollable.interior.columnconfigure(0, weight = 1)
        scrollable.interior.rowconfigure(0, weight = 1)

        frame = ttk.LabelFrame(scrollable.interior, text = 'Puzzles:')
        frame.grid(column = 0, row = 0, sticky = 'WENS')
        frame.columnconfigure(0, weight = 1)

        for i, pt in enumerate(self.tutorial.puzzles):
            puzzle = pt.puzzle

            label = WrappingLabel(frame, text = f"{i+1}. {puzzle.question}", wraplength=50)
            label.grid(row = i, column = 0, padx = 5, pady = 5, sticky="EWNS")

            button = ttk.Button(frame, text = "Solve",
                command = lambda p=puzzle: self.solve(p) # type: ignore
            )
            button.bind('<Return>', lambda e, p=puzzle: self.solve(p)) # type: ignore
            button.grid(row = i, column = 1, padx = 5, sticky="S")

            self.puzzles[puzzle] = (label, button)

        return scrollable

    def make_file_tree(self, master):
        """ Returns the file view. Sets self.file_tree to the Treeview. """
        self.file_tree = ttk.Treeview(master)

        self.update_file_tree()
        self.file_tree.tag_bind("dir", "<<TreeviewOpen>>",
            lambda e: self.update_file_tree(self.file_tree.focus()))

        return self.file_tree

    def update_file_tree(self, folder: str = ""):
        """ Updates the given folder in the file tree. Pass the iid of the node (which is the path to the file). "" is the root. """
        print(f'updating file tree for "{folder}"')

        # get old_files as dict of {path: is_open,...}
        old_files = self.file_tree.get_children(folder)
        old_files = {file: self.file_tree.item(file, option = "open") for file in old_files}

        # get new children, convert "" to "/"
        new_files = self.tutorial.get_files(PurePosixPath(folder if folder else "/")) 

        # clear existing children
        # TODO maybe keep the existing Treeview items instead of deleting them all each time?
        self.file_tree.delete(*old_files.keys()) 

        # Update the Treeview
        for is_dir, is_symlink, file in new_files:
            file_id = str(file) # Use full path as iid

            tags = ["dir"] if is_dir else ["file"]
            if is_symlink: tags.append("symlink")

            
            self.file_tree.insert(folder, tk.END, iid = file_id, text = file.name, tags = tags)
            if is_dir:
                # TODO If a directory is new, or was already open, open it. Don't open symlinks (to avoid infinite recursion)
                # Right now everything starts closed unless it was already open.
                if old_files.get(file_id, False):
                    self.file_tree.item(file_id, open = True) # open it
                    self.update_file_tree(file_id) # trigger update on the subfolder
                else:
                    self.file_tree.insert(file, tk.END) # insert a dummy child so that is shows as "openable"


    def solve(self, puzzle: Puzzle):
        solved, feedback = self.tutorial.solve_puzzle(puzzle)
        tkinter.messagebox.showinfo("Feedback", feedback)

        if solved:
            self.puzzles[puzzle][1]["state"] = "disabled"
            if all((p.solved for p in self.puzzles.keys())): # If all puzzles are solved quit.
                self.destroy()

    def report_callback_exception(self, *args):
        """ Override. """
        # TODO make this show an error box or something.
        # Error will be shown in stderr
        super().report_callback_exception(*args)
        self.destroy()