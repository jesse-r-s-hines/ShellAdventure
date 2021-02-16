from typing import Tuple, Dict
from .tutorial import Tutorial
from .support import Puzzle
from .utilities import change_user
import os, sys
from tkinter import Tk, StringVar
from tkinter import ttk
import tkinter.messagebox

class GUI:
    def __init__(self, tutorial: Tutorial):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        self.tutorial = tutorial
        # self.flagInput = StringVar(self.root, value="")

        self.root = Tk()
        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        self.puzzles: Dict[Puzzle, Tuple[ttk.Label, ttk.Button]] = {}

        self.root.title("Shell Adventure")
        self.root.minsize(600, 300) # To keep you from being able to shrink everything off the screen.
        self.root.columnconfigure(0, weight = 1, minsize = 80)
        self.root.rowconfigure(0, weight = 1, minsize = 80)

        puzzlePanel = ttk.LabelFrame(self.root, text = 'Puzzles:')
        puzzlePanel.grid(column = 0, row = 0, sticky = 'WENS')

        for i, pt in enumerate(self.tutorial.puzzles):
            label = ttk.Label(puzzlePanel, text = pt.puzzle.question)
            label.grid(column = 0, row = i)

            button = ttk.Button(puzzlePanel, text = "Solve",
                command = lambda p=pt.puzzle: self.solve(p) # type: ignore
            )
            button.bind('<Return>', lambda e, p=pt.puzzle: self.solve(p)) # type: ignore
            button.grid(column = 1, row = i)

            self.puzzles[pt.puzzle] = (label, button)

        self.root.mainloop()

    def solve(self, puzzle: Puzzle):
        solved, feedback = self.tutorial.solve_puzzle(puzzle)
        tkinter.messagebox.showinfo("Feedback", feedback)

        if solved:
            self.puzzles[puzzle][1]["state"] = "disabled"
            if all((p.solved for p in self.puzzles.keys())): # If all puzzles are solved quit.
                self.root.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
        exit(1)

    # By default, python won't make any files writable by "other". This turns that off. This will be called in docker container
    os.umask(0o000)
    with change_user("student"):
        tutorial = Tutorial(sys.argv[1], '/tmp/shell-adventure')
        tutorial.run()

        GUI(tutorial)