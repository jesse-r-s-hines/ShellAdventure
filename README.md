# About
*Shell Adventure* is a tool for making tutorials to teach the Linux command line. *Shell Adventure* sets up a containerized Linux environment using Docker that stundents can experiment in without danger of damaging their system. You can set up randomized and autograded puzzles for students to solve, and give custom feedback if the student did the puzzle incorrectly. You can run tutorials in custom Docker images with the environment set up however you want. *Shell Adventure* also shows a GUI which shows the puzzles the student needs to solve, and a visual directory tree of the environment to help students navigate the filesystem through the command line.

# Installing

## Requirements
You will need to install:
- [Python3.7+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/)

Follow the instructions from the links above to install Python and Docker on your system.

## Installing on Debian
```bash
cd ShellAdventure

# Install pip and dependencies
sudo apt install python3-pip python3-pil python3-pil.imagetk
python3 -m pip install -r requirements.txt
```

### Optional:
By default, you need to run Docker as root. Since *Shell Adventure* uses Docker, you will either have to run *Shell Adventure* as root or add your user to the `docker` group to allow running Docker:
```bash
sudo groupadd docker
sudo usermod -aG docker $USER
# Logout and login to refresh user groups.
```

## Installing on Windows
*Shell Adventure* will also work on Windows if you install [Docker for Windows](https://docs.docker.com/docker-for-windows/install), though it will generally be slower to load.
```bat
cd ShellAdventure

:: Install Dependencies
python3 -m pip install -r requirements.txt
```

## Installing on Mac
*Shell Adventure* will work using [Docker for Mac](https://docs.docker.com/docker-for-mac/install/).

```bash
cd ShellAdventure

brew install python-tk
python3 -m pip install -r requirements.txt
```

# Running
To start the tutorial, simply run the [`launch.py`](launch.py) Python script and select your tutorial YAML config file in the file selection dialog.
You can also pass the config file on the command line directly like so:
```bash
python3 launch.py <config_file>
```

This will launch the tutorial with the given configuration (see [below](#usage) for how to make a tutorial config file). It will generate any puzzles you specified and then place the student at `/home/student` in the Docker container. The student will be shown the list of puzzles in small GUI detached from the terminal and can try to solve them.

The first time you run *Shell Adventure* may take a while as it pulls the Docker image. 

If you are using Docker for Windows or Docker for Mac, make sure that the Docker engine is started before running [`launch.py`](launch.py).

# The Environnement
The tutorials will take place in a Linux command-line environnement running insside a Docker container. The default container is running a bash shell in a headless Ubuntu 20.04. See [`supported_commands.md`](docs/supported_commands.md) for a list of the commands available in the default container. The student will be logged in as user `student` with password `student` and home directory `/home/student`. The student has `sudo` privileges by default so that you can teach use of `sudo` and permissions.

If you want to add or remove commands in the container, change the user, or even which shell is used, see [Using Custom Docker Images](#using-custom-docker-images)

# Usage
You configure each tutorial with [YAML](https://yaml.org/) config files and Python scripts. The Python scripts will define a function for each puzzle template. The function will generate any files needed for the puzzle and then return a `Puzzle` object containing the puzzle question text and a callback that will autograde the puzzle. The YAML config file will specify which puzzles templates to use, and other tutorial settings.

## Configuration
The configuration file passed to the *Shell Adventure* [`launch.py`](launch.py) script controls what puzzles are used in the tutorial and various other options.

A simple config file example:
```yaml
# All paths are interpreted as relative to the config file unless they are absolute

# Required. A list of Python scripts that contain the puzzles templates for the tutorial
modules:
    - path/to/my_puzzles.py

# Required. A list of the puzzles templates that will be generated in the tutorial.
# Each puzzle is a function in one of the modules.
# Specify the functions as <module_name>.<puzzle_function_name>
# You can also "nest" puzzles. Nested puzzles will be hidden until their parent has been solved.
puzzles:
    - my_puzzles.cd_puzzle
    - my_puzzles.grep_puzzle
    - my_puzzles.copy_puzzle:
        - my_puzzles.move_puzzle # This puzzle won't be shown until my_puzzles.copy_puzzle is solved
```
For all available options see [`example_config.yaml`](examples/example_config.yaml).

## Generating and Autograding Puzzles
Puzzle templates are simply Python functions that will be run in the container, do whatever setup the puzzle requires, and return a `Puzzle` object. The puzzle templates can optionally take parameters. All parameters are optional, and order does not matter, but the parameters must have the same name as listed here:
- `root`: A `File` object representing root. Equivalent to `File("/")`
- `home`: A `File` object representing the student's home. Equivalent to `File("/home/student")` unless you've changed what the student's home in the tutorial config

```python
# import Puzzle, File, and other Shell Adventure tools
from shell_adventure.api import *

def copy(home: File):
    src = (home / "A.txt").create(content = "A\n")
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
```

Each `Puzzle` object contains a question string, a checker function, and a (optionally) score. The question in the puzzle will be shown the student. The checker function will be run whenever the student clicks "Solve" on the puzzle in the GUI, and should return `True` if the puzzle was solved correctly or `False` otherwise.

You can also indicate failure by making the checker function return a string that explains what the student did wrong. The feedback string will be shown to the student when they try to solve a puzzle incorrectly.

The checker function can take the following parameters. Like the puzzle template parameters, all parameters are optional, and order does not matter, but must have the same name as listed here:
- `flag`: If the `flag` parameter is present, an input dialog will be shown to the student when sumbitting a puzzle, and their input will be passed to this parameter as a `str`
- `cwd`: The path to the student's current working directory as a `File` object

```python
class Puzzle:
    def __init__(self, question: str, checker: AutoGrader, score: int = 1):
        """
        Construct a Puzzle object.

        Parameters:

        question:
            The question to be asked.
        checker:
            The function that will grade whether the puzzle was completed correctly or not.
            The checker function can take the following parameters. All parameters are optional, and order does not matter,
            but the parameters must have the same name as listed here:
                flag: str
                    If the flag parameter is present, an input dialog will be shown to the student when sumbitting a puzzle,
                    and their input will be passed to this parameter.
                cwd: File
                    The path to the students current directory

            The checker function should return a string or a boolean. If it returns True, the puzzle is solved. If it returns
            False or a string, the puzzle was not solved. Returning a string will show the string as feedback to the student.
        score:
            The score given on success. Defaults to 1.
        """
```

You can add helper functions in puzzle modules by making private functions (beginning with an "_"). Private functions will not be treated as puzzles.

## Users and Permissions
### Changing User
By default, your generator functions and checker functions are run as `root`, but with the `euid` and `egid` set as "student". This means that while you are technically `root`, files you create will be made as owned by `student` by default. You can switch your `euid` and `egid` back to `root` if you need to using the `change_user()` context manager:

```python
with change_user("root"):
    File("root_file").create() # root will own this file
File("student_file").create() # We are back to default user, student will own this file.
```

Note that  `os.system()` and the like will run as `root` regardles of your `euid` and `change_user` since they starts a new process. If you need to call `os.system()` directly to run a command as `student` you'll need to use the `su` command.

### Manipulating Permissions
You can manipulate permissions through the standard Python libraries such as `os` and `stat`. But *Shell Adventure* includes a more convenient API for manipulating basic file permissions. You can access and modify `File` permissions via the `File.permissions` property which returns a `LinkedPermissions` object.

Examples:
```python
>>> with change_user("root"):
>>>     file = File("root_file.txt").create()
>>> file.create(mode = 0o764) # You can specify permissions as an int directly in create
>>> file.permissions.user.read # Check current permissions
True
>>> file.permissions.group.write == True
True
>>> file.permissions.group.execute = True # Set individual permission bits
>>> file.permissions.group.write = False
>>> oct(int(file.permissions)) # Get Permissions object as int representation
'0o754'
>>> file.permissions = 0o666 # Equivalent to file.chmod(0o666)
>>> file.permissions = Permissions(user = "rwx", group = "r", others = "r") # more explicit way of setting all permissions
>>> file.permissions == File("other").permissions # You can compare the permissions directly
False
>>> file.permissions == 0o666 # You can compare the permissions with a raw int
False
```

## Randomization
*Shell Adventure* offers some tools to help in randomization. You can use the `rand()` method from `shell_adventure.api` to access a `RandomHelper` to generate random names and file content.

You can set `name_dictionary` and `content_sources` in you tutorial config file to change the text source for random file names and file content. (See  [example_config.yaml](examples/example_config.yaml))

### Random Files
You can use `File.random_file()` and `File.random_shared_folder()` to generate randomized files. This is useful for making randomized puzzle templates which and making it so each student has a different puzzle.

`File`s can be "shared". Directories made by `File.random_shared_folder()` are marked as "shared". What this means is that other calls to `File.random_shared_folder()` can include those directories in the path. The purpose of this is to avoid randomzied puzzles interfering with one another, while still allowing multiple puzzles in a single directory. For example you don't want a `rm` puzzle to "Remove directory A" as well as a puzzle to "Create A/B.txt".

It is assumed that folders made by `File.random_shared_folder()` are not used directly in the puzzles, but just used as a location for them. So you should not modify or remove folders made by `File.random_shared_folder()` other than placing more files in them. If you need to modify a directory in a puzzle, you need to make it directly with `File.random_file()`.

Examples:
```python
>>> home = File("/home/student")
>>> home.random_shared_folder()
File("/home/student/random/nested/folder")
>>> home.random_shared_folder()
File("/home/student/apple/banana")
>>> folder.mkdir(parents = True) # random_shared_folder() doesn't create the file on disk. Use mkdir() with parents = True to make the folder.
>>> # Make a random nested folder, but make the last folder not "shared" so we can safely rm it
>>> home.random_shared_folder().random_file().mkdir()
File("/home/student/orange/lime/tomato")
>>> home.random_shared_folder(create_new_chance = 0) # Will choose an existing "shared" folder
File("/home/student/orange/lime")
>>> File("/").random_shared_folder(depth = [5, 6]) # Create a folder 5 or 6 levels under root
File("/blueberry/lemon/watermellon/kiwi/strawberry")
```

## Using Custom Docker Images
If you want to customize the environment the student will be placed in, install or remove commands, or add pre-existing files you can make *Shell Adventure* use a different Docker image by specifying the name and tag of the image you want to use in the config file. You can use any image that is available on [Docker Hub](https://hub.docker.com/), or make your own custom images by making your own Dockerfile and building the image (see Docker's [docs](https://docs.docker.com/engine/reference/builder/)).

The `USER` of the image will be used as the student, and the `WORKDIR` of the image will be used as the student's "home". The `CMD` of the image should run the shell. Normally this will be `bash`, but you can also use a different shell application if you want. (Currently there are some minor issues using shells other than bash so use at your own risk.)

The easiest way to make your own Docker image is to extend from the default `shelladventure/shell-adventure` image. Note that since the `shell-adventure` image sets the `USER` to `student` you will need to set the user to `root` before installing things, and then set it back when you are done.

Example:
```Dockerfile
FROM shelladventure/shell-adventure:latest

USER root
RUN apt install -y hostnamectl
USER student
```

You can also make your own Docker images from scratch if you want to use an entirely different distro of Linux for example. You need to make sure that Python3.7+ and the Python packages `dill` and `python-lorem` are installed in the container.

Example:
```Dockerfile
FROM alpine:3

# Install stuff necessary for Shell Adventure
RUN apk add --no-cache python3 py3-pip
RUN python3 -m pip --no-cache-dir install dill python-lorem

# The student will be user "bob"
RUN adduser -D bob
USER bob
WORKDIR /home/bob

CMD ["sh"]
```

Then build your image and specify and the image tag in the config.
```bash
docker build -t my-image -f Dockerfile .
```
`config.yaml:`
```yaml
image: my-image
# ...
```

## Restart
*Shell Adventure* offers restart functionality. If the student clicks "Restart" in the GUI, the tutorial will start over in the same state it was before. Restart does not regenerate randomized puzzles, so if the student makes a mistake they can start over without having to figure out a new set of randomized puzzles. The student will have to resolve the puzzles however.

The `restart_enabled` config option can be used to turn this off. If `restart_enabled` is `false`, the student can only do a hard restart of the tutorial which will regenerate the randomized puzzles.

Note that restarting the tutorial only restores the filesystem state. So any files you created in setup scripts or puzzle generators will be restored, but processes will not be restarted. If your tutorial is relying on background processes, for instance starting a `mysql` server in a setup script, the process won't be restarted after a tutorial restart. You'll probably want to disable restart in these cases.

# *ShellAdventure* API Docs
You can use any of the standard Python libraries in your puzzle generation functions. The `shell_adventure.api` module also provides some helper classes, such as `File`, and `Permissions`. See [here](https://jessehines0.github.io/ShellAdventure/shell_adventure/api.html) for the documentation of the *ShellAdventure* API.

# Examples
See the [examples](examples) folder for complete examples of tutorial configuration and puzzle templates.

# Troubleshooting
### *Shell Adventure* crashes with `no matching manifest for ... in the manifest list entries`
This means that the [`shell-adventure`](https://hub.docker.com/repository/docker/shelladventure/shell-adventure) image on DockerHub isn't built for your architecture. You'll need to build the image manually by running `build_image.py`:
```bash
cd ShellAdventure
python3 build_image.py
```

### Launching the tutorial fails with `Fatal Python error: pyinit_main: can't initialize time`
If you get an error about `Fatal Python error: pyinit_main: can't initialize time` on the Raspberry Pi you may need to manually update libseccomp. Download the latest `libseccomp2_x.x.x-x_armhf.deb` from [here](http://ftp.us.debian.org/debian/pool/main/libs/libseccomp/) and
```bash
sudo apt install ./libseccomp2_x.x.x-x_armhf.deb
```

If you are building the Docker image yourself, it will fail with `invalid signature was encountered` if libseccomp is out of date.

# Running Tests
The project uses [mypy](http://mypy-lang.org) to do static type checking on the code. The tests are split up into two groups, those that run host-side, and those that run in the default `shell-adventure` container. Both use [pytest](https://docs.pytest.org/en/6.2.x/).

Its recommended that you setup a Python3.7 [venv](https://docs.python.org/3/library/venv.html) to run the tests since Python3.7 is the lowest version of Python *Shell Adventure* supports:
```bash
python3.7 -m venv .venv
source .venv/bin/activate # See https://docs.python.org/3/library/venv.html#creating-virtual-environments for Windows
python3 -m pip install -r requirements-dev.txt
```
Then run
```bash
python3 run_tests.py
```
to do mypy analysis and run the tests.

Any args passed to `run_tests.py` will be passed to `pytest`. Eg. to run tests matching a pattern:
```bash
python3 run_tests.py -k name_of_test
```
