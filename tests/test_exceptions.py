import pytest
from textwrap import dedent
from shell_adventure_shared import tutorial_errors
from shell_adventure_shared.tutorial_errors import *

class TestExceptions:
    def test_format_user_exc(self):
        code = dedent("""
            def func():
                raise Exception("BOOM!")

            func()
        """)

        exception = None
        try:
            exec(code)
        except Exception as e:
            exception = e
        
        expected = dedent("""
            Traceback (most recent call last):
              File "<string>", line 5, in <module>
              File "<string>", line 3, in func
            Exception: BOOM!
        """).lstrip()

        assert format_user_exc(exception) == expected