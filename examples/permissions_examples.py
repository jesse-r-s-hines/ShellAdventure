from shell_adventure.api import *

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
    file = home.random_file("py").create(content = "print('Hello World!')")

    return Puzzle(
        question = f'Make "{file.relative_to(home)}" executable',
        checker = lambda: file.permissions.user.execute == True
    )

def create_file_in_protected_folder(root: File):
    file = root.random_file()
    
    def checker():
        if file.exists():
            return True
        else:
            return "You will need to use sudo."

    return Puzzle(
        question = f'Create {file}',
        checker = checker,
    )