from shell_adventure.api import *
import filecmp

# Add puzzles for manipulating permissions.

def cd(home: File):
    dst = home.random_folder()
    dst.mkdir(parents = True)
    return Puzzle(
        question = f'Navigate to the "{dst}" folder',
        # Use the "cwd" flag to get the current working directory of the student
        checker = lambda cwd: True if cwd == dst else f"Use cd",
    )

def move(home: File):
    content = rand().paragraphs()
    src = home.random_folder().random_file("txt").create(content = content)
    dst = home.random_folder().random_file("txt") # Don't create

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
    dst = home / "B.txt"

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

# Private methods won't be used as puzzle generators
def _cmp_folders(diff: filecmp.dircmp):
    return (
        not diff.left_only and not diff.right_only and
        all(_cmp_folders(sub) for sub in diff.subdirs.values())
    )

def copy_folder():
    src = File("folder") # Files are relative to home by default
    src.mkdir()
    for _ in range(8):
        src.random_folder(depth = 2).random_file("txt").create(content = rand().paragraphs())
    dst = File("folder (copy)")

    def checker():
        # Check the folders are identical
        # (this might not work if the student modifies "folder", you could add additional checks for that)
        if src.exists() and dst.exists() and src.is_dir() and dst.is_dir():
            return _cmp_folders(filecmp.dircmp(src, dst))
        else:
            return False

    return Puzzle(
        question = 'Copy "folder" to "folder (copy)"',
        checker = checker,
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

def rm_folder(home: File):
    # Make a random folder. Don't use random_folder() as that will make a shared folder that other puzzles can generate in
    folder = home.random_file()
    folder.mkdir() 
    for _ in range(8):
        folder.random_folder().random_file("txt").create(content = rand().paragraphs())

    return Puzzle(
        question = f'Delete "{folder.relative_to(home)}"',
        checker = lambda: not folder.exists(),
    )

def create_files(home: File):
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
        checker = lambda flag: flag == key,
    )

def grep(home: File):
    bulk = home / "bulk"
    secret = bulk.random_folder(depth = (2,6)).random_file("txt")
    secret.create(content = "(secret key)")

    # Create a whole bunch of files
    for _ in range(100):
        file = bulk.random_folder(depth = (2, 6)).random_file("txt")
        file.create(content = rand().paragraphs())

    def checker(flag):
        # Compare student input as path, allow path relative to home
        if File(flag).resolve() == secret:
            return True
        else:
            return "There's a command to search lots of files."
    
    return Puzzle(
        question = 'Find the path to the file that contains "(secret key)"',
        checker = checker,
    )

def chown(home: File):
    root_file = (home / "root_file")
    # Change the user we are running to root so the file is created as root
    # You could also just create the file and then chown it to root afterwards
    with change_user("root"): 
        root_file.create()

    def checker():
        if root_file.owner() == "student" and root_file.group() == "student":
            return True
        elif root_file.group() == "root":
            return "You need to change the group as well"
        else:
            return False
    
    return Puzzle(
        question = 'Use sudo to take ownership of "root_file" (You are "student" and your password is "student")',
        checker = checker
    )

def chmod(home: File):
    file = home.random_file().create(mode = 0o600)

    return Puzzle(
        question = f'Make "{file.relative_to(home)}" world writable',
        checker = lambda: file.permissions == 0o777
    )

def chmod_executable(home: File):
    file = home.random_file("py").create(content = "print('hello world')")

    return Puzzle(
        question = f'Make "{file.relative_to(home)}" executable',
        checker = lambda: file.permissions.user.execute == True
    )