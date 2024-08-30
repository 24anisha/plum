"""Logging utilities for the whole project. This allows callers of this library to use their own logger."""
import logging
import sys

class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def set_logger(self, logger):
        self.logger = logger

    def get_logger(self):
        return self.logger
