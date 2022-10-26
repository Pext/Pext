#! /bin/bash

PYTHON_VERSION="${1}"
UBUNTU_RELEASE=$(sudo lsb_release -rs)

# Update APT repositories
sudo apt-get update

# Update pip
python3 -m pip install --user --upgrade pip

# Install vEnv
python3 -m pip install --user virtualenv

# Install curl
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install Qt
if [ "${UBUNTU_RELEASE}" = "22.04" ]; then
  sudo apt-get install -y qtbase5-dev qt5-qmake qtbase5-dev-tools qttools5-dev-tools
else
  sudo apt-get install -y qt5-default qt5-qmake qtbase5-dev-tools qttools5-dev-tools
fi

# Create the Python vEnv
python3 -m venv pext-env
source pext-env/bin/activate
python3 -m pip install --upgrade pip

# Install Tox
python3 -m pip install tox

# Install requirements
python3 -m pip install -r requirements.txt

# Generate translation
bash -xe prepare_activate_translations.sh 70 "https://hosted.weblate.org/exports/stats/pext/?format=json"
lrelease pext/pext.pro

# Run tests
xvfb-run tox -v -e py"${PYTHON_VERSION//./}"

# Build the app
rm -fR build
mkdir -p build
cd build || exit 1
bash -xve ../ci/build-app-image.sh
