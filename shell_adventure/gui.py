from typing import Tuple, Dict
from . import tutorial
from .support import Puzzle
from tkinter import ttk
from ttkthemes import ThemedTk
from tkinter import StringVar
import tkinter.messagebox

class WrappingLabel(ttk.Label):
    """Label that automatically adjusts the wrap to the size"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Configure>', lambda e: self.config(wraplength = self.winfo_width() - 5))

class GUI(ThemedTk):
    def __init__(self, tutorial: tutorial.Tutorial):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        super().__init__(theme="radiance")

        self.tutorial = tutorial
        # self.flagInput = StringVar(self, value="")

        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        self.puzzles: Dict[Puzzle, Tuple[ttk.Label, ttk.Button]] = {}

        self.title("Shell Adventure")
        self.minsize(300, 300) # To keep you from being able to shrink everything off the screen.
        self.columnconfigure(0, weight = 1, minsize = 80)
        self.rowconfigure(0, weight = 1, minsize = 80)

        puzzlePanel = ttk.LabelFrame(self, text = 'Puzzles:')
        puzzlePanel.grid(column = 0, row = 0, sticky = 'WENS')
        puzzlePanel.columnconfigure(0, weight = 1)

        for i, pt in enumerate(self.tutorial.puzzles):
            puzzle = pt.puzzle

            label = WrappingLabel(puzzlePanel, text = f"{i+1}. {puzzle.question}", wraplength=50)
            label.grid(row = i, column = 0, sticky="EWNS")

            button = ttk.Button(puzzlePanel, text = "Solve",
                command = lambda p=puzzle: self.solve(p) # type: ignore
            )
            button.bind('<Return>', lambda e, p=puzzle: self.solve(p)) # type: ignore
            button.grid(row = i, column = 1, padx = 5, sticky="S")

            self.puzzles[puzzle] = (label, button)

        self.mainloop()

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