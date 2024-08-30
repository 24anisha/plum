"""cleaning up the API and making it non specific to test generation (potentially to be renamed)"""
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
