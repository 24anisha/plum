import logging

# __name__ is name of module represented by this file (nothing above it)
# handler: sets rules for log formatting (location, when to log)
# NullHandler: clears logging handlers set by any dependent packages

# top level logger for whole project
# Every other logger will be a child of this logger
logging.basicConfig(level=logging.WARNING)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# conventional way to annotate logger
# FORMATTER = logging.formatter('%(asctime)s | %(levelname)s: %(message)s')
from .helpers import (
    fnhash,
    write_data_jsonl, 
    clone_repository, 
    get_test_package,
    fix_indentation,
    get_head_commit_hash
)

from .test_report_parsers import (
    get_pytest_test_failures,
    remove_fn_from_file
)

from .function import Function
from .parser_utils import get_functions_from_file, is_testable_file