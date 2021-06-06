# About
*ShellAdventure* is a tool for making tutorials to teach the Linux command line. *ShellAdventure* sets up a containerized Linux environment using Docker that stundents can experiment in without danger of damaging their system. You can set up randomized and autograded puzzles for students to solve, and give custom feedback if the student did the puzzle incorrectly. *ShellAdventure* also shows a GUI which shows the puzzles the student needs to solve, and a visual directory tree of the environment to help students navigate the filesystem through the command line.

# Installing

## Requirements
You will need to install:
- [Python3.7+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/)


By default, you need to run docker as root. Add your user to the docker group to allow running docker without `sudo`
```bash
sudo groupadd docker
sudo usermod -aG docker $USER
```
Logout and login to refresh user groups

## Install on Debian
```bash
# Install Dependencies 
sudo apt install python3-pil python3-pil.imagetk
python3 -m pip install -r requirements.txt # or requirements-dev.txt

# build the docker container
docker build -t shell-adventure .
```

If you get an error while building the container on the Raspberry Pi about `invalid signature was encountered` you
need to manually update libseccomp.
Download the latest `libseccomp2_x.x.x-x_armhf.deb` from [here](http://ftp.us.debian.org/debian/pool/main/libs/libseccomp/) and
```bash
sudo apt install ./libseccomp2_x.x.x-x_armhf.deb
```

# The Environnement
The tutorials will take place in a Linux command-line environnement. The container is running a bash shell in a headless Ubuntu 20.04.
See [supported_commands.md](docs/supported_commands.md) for a list of the commands available in the container. You can also install
more commands, or remove commands in the container if you want. The student will be logged in as user `student` with password `student`
and home directory `/home/student`. The student has `sudo` privileges by default so that you can teach use of `sudo` and permissions.

# Usage
You configure each tutorial with [YAML](https://yaml.org/) config files and Python scripts. The Python scripts will define a
function for each puzzle. The function will generate any files needed for the puzzle and then return a Puzzle object containing
the puzzle question text and a callback that will autograde the puzzle. 

## Running
```bash
python3 -m shell_adventure.shell_adventure <config_file>
```
This will launch the tutorial with the given configuration. It will generate any puzzles you specified and then place the student
at `/home/student` in the docker container. The student will be shown the list of puzzles, and can try to solve them.

(Launching it as a module, `python3 -m ...`, is important, *ShellAdventure* won't be able to run otherwise)

## Configuration
The configuration file passed to *ShellAdventure* can contain the following options:
```yaml
# Paths are interpreted as relative to the config file unless they are absolute

# Optional. Copies resources from disk into the container. 
# Maps dest: source, dest is relative to config file, source is relative to "/home/student" in the container
resources: 
    path/to/resource.txt: path/in/container/file.txt

# Optional. A list of Python scripts and/or bash scripts which will be run before puzzles are generated.
setup_scripts:
    - setup.py
    - setup.sh

# Required. A list of Python scripts that contain the puzzles for the tutorial
modules:
    - path/to/my_puzzles.py 

# Required. A list of the puzzles that will be generated in the tutorial.
# Each puzzle is a function in one of the modules.
# Specify the functions as <module_name>.<puzzle_function_name>
# You can also "nest" puzzles. Nested puzzles will be hidden until their parent has been solved.
puzzles:
    - my_puzzles.cd_puzzle
    - my_puzzles.grep_puzzle
    - my_puzzles.copy_puzzle:
        - my_puzzles.move_puzzle # This puzzle won't be shown until my_puzzles.copy_puzzle is solved

# Optional. Path to a dictionary file with one word on each line.
# The dictionary will be used for randomly generated names in puzzles.
# If omitted, a dictionary based on http://www.desiquintans.com/nounlist will be used
name_dictionary: my_dictionary.txt

# Optional. A list of files containing text.
# Random paragraphs from these files will be used when generating random content for files.
# If omitted, a "Lorem Ipsum" style generator will be used.
content_sources:
    - content.txt
```

## Puzzles
Puzzles are simply Python functions that will be run in the container, do whatever setup the puzzle requires,
and return a `Puzzle` object. Each puzzle object contains a question string, a checker function, and a score.
Add `from shell_adventure_docker import *` to your puzzle modules to import `Puzzle` and other tools. 

```python
class Puzzle:
    def __init__(self, question: str, checker: Callable[..., Union[str,bool]], score = 1):
        """
        Construct a Puzzle object.

        Parameters:

        question:
            The question to be asked.
        checker:
            The function that will grade whether the puzzle was completed correctly or not.
            The function can take the following parameters. All parameters are optional, and order does not
            matter, but the paramaters must have the same name as listed here.
            
            flag: str
                If the flag parameter is present, an input dialog will be shown to the student when sumbitting
                a puzzle, and their input will be passed to this parameter.
            cwd: File
                The path to the students current directory

            The function will return a string or a boolean. If it returns True, the puzzle is solved. If it returns
            False or a string, the puzzle was not solved, and the string will be shown as feedback to the student.
    
        score:
            The score given on success. Defaults to 1. 
        """
```

The question in the puzzle will be shown the student. The checker function will be run whenever the student clicks "Solve Puzzle",
and should return True if the puzzle was solved correctly, or a feedback string if the puzzle was solved incorrectly.

The generation functions can optionally take some parameters. Like the checker functions, the order of parameters does not matter,
but the names much match and all parameters are optional.

- `root`
    - File object pointint to root, `File('root')`
- `home`
    File object pointing to the student's home directory, `File('student')`

An example puzzle generator:

```
from shell_adventure_docker import *

def move():
    file = File("A.txt")
    file.write_text("A")

    def checker():
        return not file.exists() and File("B.txt").exists()

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker,
        score = 2,
    )
```

## File
You can use any of the standard Python libraries in your puzzle generation functions. The `shell_adventure_docker` module also 
provides some helper classes. `File` is an extension of [pathlib](https://docs.python.org/3/library/pathlib.html), with the
following additions:

### `File.chown(self, owner: Union[str, int] = None, group: Union[str, int] = None)`
Change owner and/or group of the given path. Automatically runs as root, you do not have to `change_user` 
to root before using `chown`. user can be a system user name or a uid; the same applies to group. At least
one argument is required. See also `os.chown()`, the underlying function.

### `File.chmod(self, mode: Union[str, int])`
Overrides `Path`'s `chmod`. Automatically runs as root, you do not have to `change_user` before using 
`chmod`. You can pass it a mode as an int, ie. `0o777` like pathlib chmod, or you can pass it a string 
that the unix `chmod` command would recognize such as "u+x". See the [chmod man page](https://linux.die.net/man/1/chmod)

### `File.children -> List[File]`
A property that returns the list of a directory's contents. Raises `NotADirectoryError` if not a directory. 
Basically an alias of `Path.iterdir()` but returns a list instead of a generator.

### `File.path -> str`
A property that returns the absolute path to this file as a string.

### `File.create(self, *, mode=0o666, exist_ok=True, recursive = True, content: str = None)`
An combined version of `Path.mkdir()`, `Path.touch()`, and `Path.write_text()`. It will `mkdir` 
missing dirs in the path if recursive is True (the default). New directories will use the default 
mode regardless of the `mode` parameter to match POSIX `mkdir -p` behavior. You can also specify 
a content string which will be written to the file.

Returns the file.

### `File.permissions -> Permissions`
A property that gets a Permissions object representing the permissions of this file, or sets 
a `File`'s permissions.

### `File.same_as(self, other: File) -> bool`
Checks if two files exist and have the same contents and permissions. Does not compare file names or paths.

### `File.random_file(self, ext = None) -> File`
Creates a File with a random name under self. The source for random names comes from the `name_dictionary` option
in the Tutorial config. The file is not created on disk and is not marked as shared. You can pass an 
extension which will be added to the random name. Will not create a file with a name that already exists. 

### `File.random_folder(self, depth: Union[int, Tuple[int, int]] = (1, 3), create_new_chance: float = 0.5) -> File`
Makes a File to a random folder under this file. Does not create the file or any parents on disk. 

The returned File can include new folders in the path with random names, and it can include existing
folders that are "shared". Folders are only "shared" if they were created via `random_folder()` or explicitly
marked shared via `mark_shared()`. 

Since folders created by `random_folder()` can be "reused" in other calls to `folder()` you should not modify 
the parent folders in puzzles. This way, folders created by puzzles won't intefere with one another, 
but multiple puzzles can still be created in the same directory. 

depth: Either an int or a (min, max) tuple. The returned file will have a depth under parent within
       the given range (inclusive)
create_new_chance: float in [0, 1]. The percentage chance that a new folder will be created even if
                   shared folders are available. 0 means it will only choose existing folders, 1 means
                   it will only create new folders.
```python
>>> home.random_folder()
File("/home/student/random/nested/folder")
>>> homd.random_folder()
File("/home/student/random/folder2")
>>> folder = home.random_folder()
# random_folder() doesn't create the file on disk. Use mkdir() with parents = True to make the folder.
>>> folder.mkdir(parents = True) 
```

### `File.mark_shared()`
Marks the a File as shared. File should be a directory, though it does not have to exist yet.

### `File.home()`
Returns the home directory of the student, `/home/student`


## Permissions
You can access and modify `File` permissions via the `File.permissions` propery, which offers a more convenient API to manipulate
UNIX file permissions than Python's [os](https://docs.python.org/3/library/os.html) and [stat](https://docs.python.org/3/library/stat.html)
modules. `File.permissions` returns a `Permissions` object.

```python
class Permissions:
    """
    Represents basic Linux permissions, with user, group, and others sections.
    Currently doesn't include special permission bits such as the sticky bit.
    """

    def __init__(self, mode: int = None, *, user: str = "", group: str = "", others: str = ""):
        """
        Create a permissions object. You can create one from an octal int, or by specifying user, group, and others
        with strings containing some combination of "rwx".
        Eg.
        >>> Permissions(0o777)
        >>> Permissions(user = "rw", group = "r", others = "")
        """

    def __eq__(self, other) -> bool:
        """ Compare permission objects. You can also compare a permission object with its octal representation. """

    def __int__(self):
        """ Returns the integer representation of the permissions. Ie. 0o777 """

    def __str__(self):
        """
        Returns the string representation of the permissions, as ls -l would.
        >>> str(Permissions(0o764))
        "rwx-rw-r--"
        """
```

Examples:
```python
>>> file = File("root_file.txt")
>>> file.create(mode=0o764)
>>> file.permissions.user.read # Check current permissions
True
>>> file.permissions.group.write == True
True
>>> file.permissions.group.execute = True # Set individual permission bits
>>> file.permissions.group.write = False
>>> int(file.permissions)
0o754
>>> file.permissions = 0o666 # Equivalent to file.chmod(0o666)
>>> file.permissions = Permissions(user = "rwx", group = "r", others = "r") # long way of setting all permissions
>>> file.permissions == File("other").permissions # You can compare the permissions directly
>>> file.permissions == 0o666 # You can compare the permissions with a raw int
```

## `change_user(user: str, group: str = None)`
By default, your generator functions are run as root, but with the `euid` and `egid` set as "student". This means
that files you create will be made as owned by student by default, but you can switch to root if you need to.
The `shell_adventure_docker` package has a `change_user` context manager which can be used to switch users easily. 

`change_user` changes the effective user of the process to user (by name), and changes it back when the context manager exits. Group will default to the group with the same name as user.

Example:
```python
from shell_adventure_docker import *

File("student_file.txt").create()
with change_user("root"):
    File("root_file.txt").create()
# We are back as student
```

Note that `os.system()` and the like will run as root regardles of `change_user` since it starts a new process.

## Randomization
*ShellAdventure* offers some tools to help in randomization. You can use the `rand` object from `shell_adventure_docker`
to generate random names and file content.

### `rand.name()`
Returns a random word that can be used as a file name. The name is taken from the name_dictionary.

### `rand.paragraphs(count: Union[int, Tuple[int, int]] = (1, 3)) -> str`

Return a random sequence of paragraphs from the content_sources.
If no content sources are provided or there isn't enough content to provide the size it will default to a lorem ipsum generator.

paramaters:
    count: Either an int or a (min, max) tuple. If a tuple is given, will return a random number of paragraphs
            in the range, inclusive.

### Random Files
You can also use `File.random_file()` and `File.random_folder()` to generate randomized files (see above).
`File`s can be "shared". Parent directories made by `File.random_folder()` are marked as "shared". What this means is
that other calls to `File.random_folder()` can include those directories in the path. The purpose of this is to avoid
puzzles interfering with one another, while still allowing multiple puzzles in a single directory. For example you don't
want a `rm` puzzle to be to remove a directory another puzzle is in.

It is assumed that folders made by 'File.random_folder()` are not used directly in the puzzles, but just used as a location
for them. So you should not modify or remove folders made by `File.random_folder()` other than placing more files in them.
If you need to modify a directory in a puzzle, you need to make it directly with `mkdir()`.

# Examples

`mypuzzles.py`
```python
from shell_adventure_docker import *

def move(home): # home will be passed File('/home/student')
    # Create a random txt file under home
    content = rand.paragraphs(3)
    src = home.random_file("txt").create(content = content) 
    dst = home.random_folder().random_file("txt") # Create a random destination path. Don't write it to disk.

    def checker():
        if dst.exists():
            if not src.exists() and dst.read_text() == content:
                return True # Puzzle solved!
            elif src.exists():
                return 'You need to "mv" not "cp"' # Feedback
        else:
            return 'Try looking at "man mv"' # Feedback

    return Puzzle(
        question = f'Move "{src.relative_to(home)}" to "{dst.relative_to(home)}"',
        checker = checker
    )


def cd_puzzle():
    # Puzzle generation working directory is in "/home/student" so Files are automatically relative to "/home/student"
    folder = File("myfolder") 
    folder.mkdir()

    def checker(cwd): # cwd will be passed the student's current working directory
        # You need to resolve() a relative File before you can compare them for equality.
        # You don't have to return feedback, returning False will show the student an "Incorrect!" message.
        return cwd == folder.resolve() 

    return Puzzle(
        question = f"cd into myfolder",
        checker = checker
    )

def cat():
    File("secret.txt").write_text("42\n")

    return Puzzle(
        question = f"Find the number in secret.txt",
        # An text dialog will be shown when solving this puzzle, and flag will be the input
        checker = lambda flag: flag == "42", 
    )
```

`config.yaml`
```yaml
modules:
    - my_puzzles.py 

puzzles:
    - my_puzzles.move
    - my_puzzles.cd_puzzle
    - my_puzzles.cat
```

Run:
```bash
python3 -m shell_adventure.shell_adventure config.yaml
```

# Running Tests
The tests are split up into two groups, those that run host-side, and those that run in the container. Both use [pytest](https://docs.pytest.org/en/6.2.x/).

```bash
# Run host-side tests
python3 -m pytest --cov --cov-report term

# Run docker tests
TEST_DIR=/usr/local/shell_adventure_docker_tests
docker run -t --rm --user="root" --workdir="$TEST_DIR" shell-adventure:test pytest --cov=shell_adventure_docker --cov-report term "$TEST_DIR"
```