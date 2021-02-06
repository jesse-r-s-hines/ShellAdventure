def move_1(file_system):
    file_system.run_command("echo 'move1' > A.txt")

    def checker(file_system):
        aCode, _ = file_system.run_command("test -f A.txt")
        bCode, _ = file_system.run_command("test -f B.txt")
        return (aCode == 1) and (bCode == 0)

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker
    )

def move_2(file_system):
    file_system.run_command("echo 'move2' > C.txt")

    def checker(file_system):
        cCode, _ = file_system.run_command("test -f C.txt")
        dCode, _ = file_system.run_command("test -f D.txt")
        return (cCode == 1) and (dCode == 0)

    return Puzzle(
        question = f"Rename C.txt to D.txt",
        checker = checker
    )