#!/bin/sh

# Run MyPy to check all type hinting for correctness
mypy --silent-imports pext/__main__.py pext/helpers/pext_base.py
