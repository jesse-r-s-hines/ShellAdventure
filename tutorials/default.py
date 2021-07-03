from shell_adventure_docker import *

def move():
    src = File("A.txt")
    src.write_text("A")

    def checker():
        dst = File("B.txt")
        if dst.exists():
            if not src.exists() and dst.read_text() == "A":
                return True # Solved
            elif src.exists():
                return 'You need to "mv" not "cp"'
        else:
            return 'Try looking at "man mv"'

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker
    )

def copy(home):
    src = home / "C.txt"
    src.write_text("C")

    def checker():
        dst = home / "D.txt"
        if dst.exists():
            if src.exists() and dst.read_text() == "C":
                return True
            elif not src.exists():
                return 'You need to "cp" not "mv"'
        else:
            return 'Try looking at "man cp"'

    return Puzzle(
        question = f"Copy C.txt to D.txt",
        checker = checker
    )

def cat():
    file = File("secret.txt")
    file.write_text("42\n")

    return Puzzle(
        question = f"What's in secret.txt?",
        checker = lambda flag: flag == "42",
    )


def random_puzzle(home):
    src = home.random_file("txt")
    src.write_text(rand().paragraphs(3))
    
    dst = home.random_folder().random_file("txt") # Don't create yet

    return Puzzle(
        question = f"Move {src.relative_to(home)} to {dst.relative_to(home)}",
        checker = lambda: not src.exists() and dst.exists()
    )