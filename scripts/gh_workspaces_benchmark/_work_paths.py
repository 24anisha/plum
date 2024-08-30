import os


def get_default_repo_list_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '_raw_list', 'repo_list.txt')

def get_default_lang_list_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '_raw_list', 'repo_with_langs.txt')

def get_default_working_directory():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '_benchmark_output')

def get_default_repo_directory():
    return os.path.join(get_default_working_directory(), 'repos')
