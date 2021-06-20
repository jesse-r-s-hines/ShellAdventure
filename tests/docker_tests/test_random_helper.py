import pytest
from shell_adventure_docker.random_helper import RandomHelper, RandomHelperException

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

    def test_random_folder_basic(self, tmp_path):
        random = RandomHelper("a\nb\nc\nd\ne")

        file = random.folder(tmp_path)
        assert tmp_path in file.parents
        assert not file.exists()

        file = random.folder(tmp_path, depth = 2)
        assert file in random._shared_folders
        assert file.parents[0] in random._shared_folders
        assert file.parents[1] not in random._shared_folders

    def test_random_folder(self, tmp_path):
        random = RandomHelper("a\nb\n")

        file1 = random.folder(tmp_path, depth = 1)
        assert file1.parent == tmp_path
        assert file1.name in ["a", "b"]

        file2 = random.folder(file1, depth = 1, create_new_chance=0)
        assert file2.parent == file1
        assert file2.name in ["a", "b"]

    def test_random_folder_already_exists(self, tmp_path):
        random = RandomHelper("a\nb\n")
        (tmp_path / "a").mkdir()

        assert random.folder(tmp_path, depth = 1, create_new_chance = 1).name == "b"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.folder(tmp_path, depth = 1, create_new_chance = 1) # "a" already exists, "b" was generated.

    def test_mark_shared(self, tmp_path):
        random = RandomHelper("a\nb\nc\nd\ne")

        random.mark_shared(tmp_path)
        assert tmp_path in random._shared_folders

        (tmp_path / "file.txt").touch()
        with pytest.raises(RandomHelperException, match="Can only mark folders as shared"):
            random.mark_shared(tmp_path / "file.txt")


        file1 = random.folder(tmp_path, depth = 1)
        assert file1.parent == tmp_path

        file2 = random.folder(file1, depth = 1, create_new_chance=0)
        assert file2.parent == file1

    def test_random_file(self, tmp_path):
        random = RandomHelper("a\nb\n")

        file = random.file(tmp_path)
        assert file.parent == tmp_path
        assert file.name in ["a", "b"]

        file = random.file(tmp_path, "txt")
        assert file.name in ["a.txt", "b.txt"]

    def test_random_file_already_exists(self, tmp_path):
        random = RandomHelper("a\nb\n")
        (tmp_path / "a").touch()
        assert random.file(tmp_path).name == "b"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.file(tmp_path) # "a" already exists, "b" was generated.

        random = RandomHelper("a\nb\n")
        (tmp_path / "a.txt").touch()
        assert random.file(tmp_path, ext = "txt").name == "b.txt"

        with pytest.raises(RandomHelperException, match = "Out of unique names"):
            random.file(tmp_path) # "a.txt" already exists, "b" was generated.