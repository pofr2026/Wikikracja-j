#!/usr/bin/env python
"""
Command-line utility for administrative tasks.
"""

# Standard library imports
import os
import sys

# Third party imports
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zzz.settings")

    execute_from_command_line(sys.argv)
