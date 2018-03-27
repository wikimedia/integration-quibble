import os.path


def is_in_docker():
    return os.path.exists('/.dockerenv')
