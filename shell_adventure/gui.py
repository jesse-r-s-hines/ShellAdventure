from __future__ import annotations # Don't evaluate annotations until after the module is run.
from typing import Tuple, Dict
from . import tutorial
from .support import Puzzle
from tkinter import Tk, StringVar
from tkinter import ttk
import tkinter.messagebox

class GUI(Tk):
    def __init__(self, tutorial: tutorial.Tutorial):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        super().__init__()

        self.tutorial = tutorial
        # self.flagInput = StringVar(self, value="")

        # map puzzles to their question label and button. By default, Python will use object identity for dict keys, which is what we want.
        self.puzzles: Dict[Puzzle, Tuple[ttk.Label, ttk.Button]] = {}

        self.title("Shell Adventure")
        self.minsize(600, 300) # To keep you from being able to shrink everything off the screen.
        self.columnconfigure(0, weight = 1, minsize = 80)
        self.rowconfigure(0, weight = 1, minsize = 80)

        puzzlePanel = ttk.LabelFrame(self, text = 'Puzzles:')
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