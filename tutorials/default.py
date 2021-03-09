def move_1():
    file = File("A.txt")
    file.write_text("A")

    def checker():
        return not file.exists() and File("B.txt").exists()

    return Puzzle(
        question = f"Rename A.txt to B.txt",
        checker = checker
                )

def move_2():
    file = File("C.txt")
    file.write_text("C")

    def checker():
        return not file.exists() and File("D.txt").exists()

    return Puzzle(
        question = f"Rename C.txt to D.txt",
        checker = checker
    )