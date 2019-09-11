import os


def read(file_name):
    """Read a text file and return the content as a string."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root_dir, file_name), encoding='utf-8') as f:
        return f.read().strip()


__version__ = read('VERSION')
