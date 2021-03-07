from __future__ import annotations # Don't evaluate annotations until after the module is run.
from typing import Tuple, Dict
from . import tutorial
from .support import Puzzle
from tkinter import Tk, StringVar
from tkinter import ttk
import tkinter.messagebox

class GUI:
    def __init__(self, tutorial: tutorial.Tutorial):
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
            puzzle = pt.puzzle

            label = ttk.Label(puzzlePanel, text = puzzle.question)
            label.grid(column = 0, row = i)

            button = ttk.Button(puzzlePanel, text = "Solve",
                command = lambda p=puzzle: self.solve(p)
            )
            button.bind('<Return>', lambda e, p=puzzle: self.solve(p))
            button.grid(column = 1, row = i)

            self.puzzles[puzzle] = (label, button)

        self.root.mainloop()

    def solve(self, puzzle: Puzzle):
        solved, feedback = self.tutorial.solve_puzzle(puzzle)
        tkinter.messagebox.showinfo("Feedback", feedback)

        if solved:
            self.puzzles[puzzle][1]["state"] = "disabled"
            if all((p.solved for p in self.puzzles.keys())): # If all puzzles are solved quit.
                self.root.destroy()
