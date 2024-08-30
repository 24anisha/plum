"Useful context managers"

from contextlib import contextmanager
import os


@contextmanager
def temporary_path_change_to(new_path: str):
    old_path = os.getcwd()
    os.chdir(new_path)
    try:
        yield
    finally:
        os.chdir(old_path)

