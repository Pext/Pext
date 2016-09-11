#!/bin/sh

# Run MyPy to check all type hinting for correctness
mypy --silent-imports pext/__main__.py pext/helpers/pext_base.py

# Run prospector to find general style issues
prospector
