# shell_adventure.api includes the functionality you will need to create puzzle templates.
from shell_adventure.api import *

# Generator functions can optionally have parameters. For instance "home" will be passed File("/home/student")
# You could also just call File("/home/student") in the puzzle template if you wanted.
def cd(home: File):
    # Create a File to a random nested folder. The folder is not made on disk until we call mkdir
    dst = home.random_shared_folder()
    dst.mkdir(parents = True, exist_ok = True) # Make the folder and its parents

    # The checker function can optionally have parameters.
    # "cwd" will be passed the current working directory of the student
    def checker(cwd):
        if cwd == dst:
            return True
        else:
            # You can return False or a string to indicate failure. The string will be shown to the student
            # as feedback
            return "Use cd"

    return Puzzle(
        question = f'Navigate to the "{dst}" folder',
        checker = checker
    )

def move(home: File):
    content = rand().paragraphs()
    src = home.random_shared_folder().random_file("txt").create(content = content)
    dst = home.random_shared_folder().random_file("txt") # Don't create on disk

    def checker():
        if dst.exists():
            if not src.exists() and dst.read_text() == content:
                return True # Solved
            elif src.exists():
                return 'You need to "mv" not "cp"'
        return 'Try looking at "man mv"'

    return Puzzle(
        question = f'Rename "{src.relative_to(home)}" to "{dst.relative_to(home)}"',
        checker = checker
    )

def copy(home: File):
    src = home / "A.txt"
    src.create(content = "A\n")
    dst = home / "B.txt" # Don't create on disk

    def checker():
        if dst.exists():
            if src.exists() and dst.read_text() == "A\n":
                return True
            elif not src.exists():
                return 'You need to "cp" not "mv"'
        return 'Try looking at "man cp"'

    return Puzzle(
        question = f"Copy A.txt to B.txt",
        checker = checker
    )

def rm(home: File):
    file = (home / "DELETEME").create(content = "DELETEME")

    def checker():
        if not file.exists():
            return True
        else:
            return "Look at 'man rm'"

    return Puzzle(
        question = "Delete DELETEME",
        checker = checker,
    )

def create_file(home: File):
    file = home.random_file().random_file()

    def checker():
        if file.exists():
            return True
        else:
            return "You need to make the parent directory, then the file."

    return Puzzle(
        question = f'Create {file.relative_to(home)}',
        checker = checker,
    )

def cat():
    key = rand().name()
    File("secret.txt").create(content = f"{key}\n")

    return Puzzle(
        question = f"What's in 'secret.txt'?",
        # If you have the "flag" parameter, the GUI will bring up a input box when you try to solve the puzzle
        # and pass the input to the checker.
        checker = lambda flag: flag == key,
    )
