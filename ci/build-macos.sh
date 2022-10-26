#! /bin/bash

PYTHON_VERSION="${1}"

# Install Tox
pip3 install tox

# Generate translation
brew install qt jq
bash prepare_activate_translations.sh 70 "https://hosted.weblate.org/exports/stats/pext/?format=json"
PATH="/usr/local/opt/qt/bin:$PATH" lrelease pext/pext.pro

# Run tests
tox -v -e py"${PYTHON_VERSION//./}"

# Build the app
bash -xve ci/build-dmg.sh
