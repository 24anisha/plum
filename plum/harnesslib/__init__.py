import logging

# __name__ is name of module represented by this file (nothing above it)
# handler: sets rules for log formatting (location, when to log)
# NullHandler: clears logging handlers set by any dependent packages
# logging.getLogger(__name__).addHandler(logging.NullHandler())

# conventional way to annotate logger
# top level logger for whole project
# Every other logger will be a child of this logger
logging.getLogger(__name__).addHandler(logging.NullHandler())

# FORMATTER = logging.formatter('%(asctime)s | %(levelname)s: %(message)s')
