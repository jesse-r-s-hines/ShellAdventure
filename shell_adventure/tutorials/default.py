from os import system

def move_1():
    system("echo 'move1' > A.txt")

    def checker():
        aCode = system("test -f A.txt")
        bCode = system("test -f B.txt")
        print(aCode, bCode)
        return (aCode >= 1) and (bCode == 0)

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker
    )

def move_2():
    system("echo 'move2' > C.txt")

    def checker():
        cCode = system("test -f C.txt")
        dCode = system("test -f D.txt")
        return (cCode >= 1) and (dCode == 0)

    return Puzzle(
        question = f"Rename C.txt to D.txt",
        checker = checker
    )