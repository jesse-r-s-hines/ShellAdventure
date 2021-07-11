from shell_adventure.api import *
# You can of course use any of Python's default libraries. filecmp is particularly useful.
import filecmp 

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
        src.random_shared_folder(depth = 2).random_file("txt").create(content = rand().paragraphs())
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

def rm_folder(home: File, root: File):
    # Make a random folder. Don't use random_shared_folder() as that will make a shared folder that other puzzles can generate in
    folder = home.random_file()
    folder.mkdir() 
    for _ in range(8):
        folder.random_shared_folder().random_file("txt").create(content = rand().paragraphs())

    return Puzzle(
        question = f'Delete "{folder.relative_to(home)}"',
        checker = lambda: not folder.exists(),
    )

def grep(home: File):
    bulk = home / "bulk"
    secret = bulk.random_shared_folder(depth = (2,6)).random_file("txt")
    secret.create(content = "(secret key)")

    # Create a whole bunch of files
    for _ in range(100):
        file = bulk.random_shared_folder(depth = (2, 6)).random_file("txt")
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

