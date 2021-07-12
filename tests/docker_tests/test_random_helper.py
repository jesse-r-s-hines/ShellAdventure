import pytest
from pathlib import Path
from shell_adventure.api.random_helper import RandomHelper, RandomHelperException

CONTENT_1 = """
Sentence a.  Sentence b.  Sentence c.

Sentence d. Sentence e.

Sentence f.
"""

CONTENT_2 = """

    Space indented paragraph.



\tTab indented paragraph.


"""

CONTENT_3 = "One line."

class TestRandomHelper:
    def test_name(self):
        random = RandomHelper(
            name_dictionary = "apple\n\n\n\nbanana\norange\n",
            content_sources = "",
        )

        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}
        assert random.name() in {"apple", "banana", "orange"}

        with pytest.raises(RandomHelperException, match="Out of unique names"):
            random.name()

    def test_paragraphs(self):
        random = RandomHelper("", [CONTENT_1])
        paras = ["Sentence a.  Sentence b.  Sentence c.\n", "Sentence d. Sentence e.\n", "Sentence f.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras

        for _ in range(10): # random range
            assert len(random.paragraphs((1, 3)).split("\n\n")) in [1, 2, 3]

        for _ in range(10):
            all = random.paragraphs(3)
            assert all == "Sentence a.  Sentence b.  Sentence c.\n\nSentence d. Sentence e.\n\nSentence f.\n"

        # Will make lorem ipsum text if size is to big.
        assert "Sentence" not in random.paragraphs(10)


    def test_whitespace(self):
        random = RandomHelper("", [CONTENT_2])
        # indentation should be preserved
        paras = ["    Space indented paragraph.\n", "\tTab indented paragraph.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras

    def test_one_line(self):
        random = RandomHelper("", [CONTENT_3])
        assert random.paragraphs(1) == "One line.\n"


    def test_multiple_files(self):
        random = RandomHelper("", [CONTENT_1, CONTENT_2])
        paras1 = ["Sentence a.  Sentence b.  Sentence c.\n", "Sentence d. Sentence e.\n", "Sentence f.\n"]
        paras2 = ["    Space indented paragraph.\n", "\tTab indented paragraph.\n"]

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert random.paragraphs(1) in paras1 + paras2

        for _ in range(10): # Only CONTENT_1 has 3 paragraphs. Won't combine files.
            assert random.paragraphs(3) == "Sentence a.  Sentence b.  Sentence c.\n\nSentence d. Sentence e.\n\nSentence f.\n"

        for _ in range(10): # Lorem ipsum since there is no file that is big enough.
            assert "Sentence" not in random.paragraphs((4, 10))

    def test_no_content_sources(self):
        random = RandomHelper("")

        for _ in range(10): # Should not use lorem ipsum since we are within range.
            assert len(random.paragraphs(10).split("\n\n")) == 10
            assert random.paragraphs(10).endswith("\n")

    def test_random_folder_basic(self, working_dir: Path):
        random = RandomHelper("a\nb\nc\nd\ne")

        file = random.folder(working_dir)
        assert file in random._shared_folders
        assert working_dir in file.parents
        assert not file.exists()

        file = random.folder(str(working_dir), depth = 2)
        assert file in random._shared_folders
        assert file.parents[0] in random._shared_folders
        assert file.parents[1] not in random._shared_folders

    def test_random_folder(self, working_dir: Path):
        random = RandomHelper("a\nb\nc\n")

        folder1 = random.folder(working_dir, depth = 1)
        assert folder1.parent == working_dir
        assert folder1.name in ["a", "b", "c"]
        folder1.mkdir()

        # folder1 is empty so even with create_new_chance = 0 it will create a new path.
        folder2 = random.folder(folder1, depth = 1, create_new_chance = 0)
        assert folder2.parent == folder1
        assert folder2.name in ["a", "b", "c"]
        assert not folder2.exists()

        # will always choose folder1
        folder3 = random.folder(working_dir, depth = 1, create_new_chance = 0)
        assert folder3 == folder1

    def test_random_folder_already_exists(self, working_dir: Path):
        random = RandomHelper("a\nb\n")
        (working_dir / "a").mkdir()

        assert random.folder(working_dir, depth = 1, create_new_chance = 1).name == "b"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.folder(working_dir, depth = 1, create_new_chance = 1) # "a" already exists, "b" was generated.

    def test_random_folder_only_chooses_folders_on_disk(self, working_dir: Path):
        random = RandomHelper("\n".join(map(str, range(20))))

        created_file = random.file(working_dir, "txt")
        created_file.touch()
        created_folder = random.folder(working_dir, depth = 1)
        created_folder.mkdir()
        uncreated_folder = random.folder(working_dir, depth = 1)

        assert created_folder in random._shared_folders
        assert uncreated_folder in random._shared_folders

        for i in range(10): # Will not use the shared uncreated_folder
            new = random.folder(working_dir, depth = 2, create_new_chance = 0)
            assert new.parent == created_folder

    def test_mark_shared(self, working_dir: Path):
        random = RandomHelper("a\nb\nc\nd\ne")

        random.mark_shared(working_dir)
        assert working_dir in random._shared_folders

        (working_dir / "file.txt").touch()
        with pytest.raises(RandomHelperException, match="Can only mark folders as shared"):
            random.mark_shared(working_dir / "file.txt")


        file1 = random.folder(working_dir, depth = 1)
        assert file1.parent == working_dir

        file2 = random.folder(file1, depth = 1, create_new_chance=0)
        assert file2.parent == file1

    def test_random_file(self, working_dir: Path):
        random = RandomHelper("a\nb\n")

        file = random.file(working_dir)
        assert file.parent == working_dir
        assert file.name in ["a", "b"]

        file = random.file(working_dir, "txt")
        assert file.name in ["a.txt", "b.txt"]

    def test_random_file_already_exists(self, working_dir: Path):
        random = RandomHelper("a\nb\n")
        (working_dir / "a").touch()
        assert random.file(working_dir).name == "b"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.file(working_dir) # "a" already exists, "b" was generated.

        random = RandomHelper("a\nb\n")
        (working_dir / "a.txt").touch()
        assert random.file(working_dir, ext = "txt").name == "b.txt"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.file(working_dir) # "a.txt" already exists, "b" was generated.