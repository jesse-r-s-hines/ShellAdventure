from shell_adventure.tutorial import Tutorial, Puzzle, PathLike
import sys, threading, subprocess
from tkinter import Tk, StringVar
from tkinter import ttk
import tkinter.messagebox

class GUI:
    def __init__(self, tutorial: Tutorial):
        """ Creates and launches the Shell Adventure GUI. Pass it the tutorial object. """
        self.tutorial = tutorial
        # self.flagInput = StringVar(self.root, value="")

        self.root = Tk()
        self.root.title("Shell Adventure")
        self.root.minsize(600, 300) # To keep you from being able to shrink everything off the screen.
        self.root.columnconfigure(0, weight = 1, minsize = 80)
        self.root.rowconfigure(0, weight = 1, minsize = 80)

        puzzlePanel = ttk.LabelFrame(self.root, text = 'Puzzles:')
        puzzlePanel.grid(column = 0, row = 0, sticky = 'WENS')

        for i, pt in enumerate(self.tutorial.puzzles):
            ttk.Label(puzzlePanel, text = pt.puzzle.question).grid(column = 0, row = i)
            button = ttk.Button(puzzlePanel, text = "Solve",
                command = lambda p=pt.puzzle: self.solve(p)
            )
            button.bind('<Return>', lambda e, p=pt.puzzle: self.solve(p))
            button.grid(column = 1, row = i)

        self.root.mainloop()

    def solve(self, puzzle: Puzzle):
        feedback = self.tutorial.solve_puzzle(puzzle)
        print("feedback:", feedback)
        if feedback == True:
            feedback = "Correct!"
        elif feedback == False:
            feedback = "Incorrect!"
        # else its a string
        tkinter.messagebox.showinfo("Feedback", feedback)



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("No tutorial config file given.")
    else:
        config = sys.argv[1]
        tutorial = Tutorial(config)
        tutorial.run()

        bash_session = threading.Thread( 
            # TODO I this will only work if you happen to have gnome-terminal. Change this once I have an embedded terminal
            # TODO I'd prefer not to call processes from the command line. At the very least I should use the array format instead
            # of raw shell. And I'd prefer if I could use dockerpty.
            target = lambda container: subprocess.call(f"gnome-terminal -- docker exec -it {container} bash", shell=True),
            args = (tutorial.file_system.container.id,)
        )
        bash_session.start()

        GUI(tutorial)


