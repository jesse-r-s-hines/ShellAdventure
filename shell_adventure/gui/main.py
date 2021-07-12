from typing import Callable, Tuple, Dict
from pathlib import PurePosixPath
import tkinter as tk
from tkinter import StringVar, ttk, font, messagebox
import tkinter.simpledialog as simpledialog
from ttkthemes import ThemedTk
from PIL import ImageTk, Image
from .gui_widgets import WrappingLabel, SelectableMessage, popup_box
from .scrolled_frame import VerticalScrolledFrame
from shell_adventure.host_side import tutorial
from shell_adventure.shared.puzzle_data import PuzzleData
from . import PKG_PATH

class ShellAdventureGUI(ThemedTk):
    def __init__(self, tutorial: tutorial.Tutorial, restart_callback: Callable):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        super().__init__(theme="radiance")

        self.tutorial = tutorial
        self.restart_callback = restart_callback
        self.student_cwd: PurePosixPath = None # The path to the student's current directory
        self.file_tree_root = PurePosixPath("/") # The root of the displayed file tree

        self.icons = self._get_icons() # We have to keep a reference to the icons or they will get deleted
        self.file_tree: ttk.Treeview = None
        self.file_icons = self._get_file_icons()

        self.time_label = StringVar(self, value = "Time: 00:00")
        self.score_label = StringVar(self, value = "Score: 0/10")

        self.title("Shell Adventure")
        self.minsize(300, 100) # To keep you from being able to shrink everything off the screen.
        self.columnconfigure(0, weight = 1, minsize = 80)
        self.rowconfigure(0, weight = 0)
        self.rowconfigure(1, weight = 1, minsize = 80)
        self.rowconfigure(2, weight = 0)
        self.rowconfigure(3, weight = 0)

        status_bar = self._make_status_bar(self)
        status_bar.pack(side = tk.TOP, fill = tk.BOTH)

        self.file_tree = None
        if self.tutorial.show_tree:
            self.file_tree = self._make_file_tree(self)
            self.file_tree.pack(side = tk.TOP, expand = True, fill = tk.BOTH)

        button_frame = self._make_button_frame(self)
        # Set this to expand if file_tree is turned off. We need to have something that will expand
        # or we'll end up with weird looking un-rendered space. Expanding the scroll_frame canvas causes
        # issues, so lets just make the button frame expand to fill the extra space.
        button_frame.pack(side = tk.TOP, expand = not self.file_tree, fill = tk.BOTH)

        scroll_frame, self.puzzle_frame = self._make_puzzle_frame(self)
        scroll_frame.pack(side = tk.BOTTOM, expand = False, fill = tk.BOTH)
        self.update_puzzle_frame()

        def update_loop():
            self.update_gui()
            self.after(250, update_loop)
        update_loop()

        self.start_timer_loop()

        self.mainloop()

    def _get_icons(self) -> Dict[str, ImageTk.PhotoImage]:
        """ Returns a map of icons. """
        icons = {} # We have to save the icons or tkinter will let the image get garbage collected
        for file in (PKG_PATH / "icons").glob("*.png"):
            img = Image.open(file).resize((16, 16), Image.ANTIALIAS)
            icons[file.stem] = ImageTk.PhotoImage(img)
        return icons

    def _get_file_icons(self) -> Dict[Tuple[bool, bool], ImageTk.PhotoImage]:
        """ Returns a map of icons representing 4 file types. Maps (is_dir, is_symlink) tuples to the icons """
        icon_files = {
            (False, False): "file",
            (False, True ): "file_symlink",
            (True,  False): "folder",
            (True,  True ): "folder_symlink",
        }
        return {tup: self.icons[icon] for tup, icon in icon_files.items()}

    def _make_status_bar(self, master):
        """ Returns the status bar that displays time and current score. """
        status_bar = ttk.Frame(master)

        ttk.Label(status_bar, textvariable = self.score_label).pack(side = tk.RIGHT, padx = 5) # Score: 0/10
        ttk.Separator(status_bar, orient='vertical').pack(side = tk.RIGHT, fill = tk.Y, padx = 5)
        ttk.Label(status_bar, textvariable = self.time_label).pack(side = tk.RIGHT) # Time: 01:5
        ttk.Separator(status_bar, orient='vertical').pack(side = tk.RIGHT, fill = tk.Y, padx = 5)

        return status_bar

    def _make_file_tree(self, master):
        """ Returns the file view """
        file_tree = ttk.Treeview(master, show="tree") # don't show the heading

        file_tree.tag_configure("cwd", font = font.Font(weight="bold"))

        def on_open(e):
            item = file_tree.focus()
            if not file_tree.tag_has("loaded", item):
                self.load_folder(item)

        file_tree.tag_bind("dir", "<<TreeviewOpen>>", on_open)

        return file_tree

    def _make_button_frame(self, master):
        """ Returns a frame showing the restart button """
        button_frame = ttk.Frame(master)

        if self.tutorial.restart_enabled:
            restart_button = ttk.Button(button_frame,
                text = "Restart", image = self.icons["restart"], compound = "left",
                command = lambda: self.restart()
            )
            restart_button.pack(side = tk.LEFT)

        about = (
            'Welcome to the Shell Adventure command line tutorial! Complete the list of puzzles by entering commands in '
            'the detached terminal window and then clicking "Solve" when you think you\'ve completed the puzzle.\n'
            '\n'
            'Visit [GitHub](https://github.com/JesseHines0/ShellAdventure) for more documentation or to contribute!\n'
            '\n'
            'Credits:\n'
            '    Icons from [icons8](https://icons8.com)'
        )

        about_button = ttk.Button(button_frame,
            text = "About", image = self.icons["info"], compound = "left",
            # command = lambda: messagebox.showinfo("About", about)
            command = lambda: popup_box("About", about)
        )
        about_button.pack(side = tk.LEFT)

        return button_frame

    def _make_puzzle_frame(self, master) -> Tuple[VerticalScrolledFrame, ttk.LabelFrame]:
        """ Returns a scrollable frame and the frame the puzzles will be on."""
        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        scroll_frame = VerticalScrolledFrame(master)
        scroll_frame.interior.columnconfigure(0, weight = 1)
        scroll_frame.interior.rowconfigure(0, weight = 1)

        puzzle_frame = ttk.LabelFrame(scroll_frame.interior, text = 'Puzzles:')
        puzzle_frame.grid(column = 0, row = 0, sticky = 'WENS')
        puzzle_frame.columnconfigure(0, weight = 1)

        return scroll_frame, puzzle_frame

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

    def update_puzzle_frame(self):
        """ Remakes the puzzle list. """
        for widget in self.puzzle_frame.winfo_children(): # Should only contain one element
            widget.destroy()

        for i, puzzle in enumerate(self.tutorial.get_current_puzzles()):
            label = WrappingLabel(self.puzzle_frame, text = f"{i+1}. {puzzle.question}", wraplength=50)
            label.grid(row = i, column = 0, padx = 5, pady = 5, sticky="EWNS")

            button = ttk.Button(self.puzzle_frame,
                text = "Solved" if puzzle.solved else "Solve",
                command = lambda p=puzzle: self.solve_puzzle(p), # type: ignore
                state = "disabled" if puzzle.solved else "enabled"
            )
            button.bind('<Return>', lambda e, p=puzzle: self.solve_puzzle(p)) # type: ignore
            button.grid(row = i, column = 1, padx = 5, sticky="S")

    def _tree_node_to_path(self, iid: str):
        """ Returns the path in the container that corresponds to the given Treeview node. """
        return PurePosixPath(iid if iid else self.file_tree_root)

    def _path_to_tree_node(self, path: PurePosixPath):
        """ Returns the Treeview node id that represents the path in the container. """
        return str(self.student_cwd) if self.student_cwd != self.file_tree_root else ""


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

        # get new children
        new_files = self.tutorial.get_files(self._tree_node_to_path(folder))
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
                file_text += " <--"

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
        if self.file_tree:
            old_cwd = self.student_cwd
            self.student_cwd = self.tutorial.get_student_cwd()
            self.load_folder("")

            if self.student_cwd != old_cwd: # Jump to cwd if we've changed it
                # open all parents and scroll to (parents should already be open)
                self.file_tree.see(self._path_to_tree_node(self.student_cwd)) # type: ignore

        self.score_label.set(f"Score: {self.tutorial.current_score()}/{self.tutorial.total_score()}")

    def solve_puzzle(self, puzzle: PuzzleData):
        do_check = True
        flag = None
        if "flag" in puzzle.checker_args:
            flag = simpledialog.askstring("Input", puzzle.question, parent = self)
            if flag == None: do_check = False # If you "cancel" don't run autograder

        if do_check:
            solved, feedback = self.tutorial.solve_puzzle(puzzle, flag)
            messagebox.showinfo("Feedback", feedback)

            if solved:
                self.update_puzzle_frame()
                if self.tutorial.is_finished(): # then quit the tutorial
                    self.destroy()

    def restart(self):
        self.tutorial.restart()
        self.restart_callback()
        self.update_puzzle_frame()

    def report_callback_exception(self, exc, val, tb):
        """ Override. """
        self.destroy()
        # Raising the exception so that we can handle it in the launch script
        raise val
