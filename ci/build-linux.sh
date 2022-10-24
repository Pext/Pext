#! /bin/bash

UBUNTU_RELEASE=$(sudo lsb_release -rs)

# Update APT repositories
sudo apt-get update

# Install Python
if [ "${UBUNTU_RELEASE}" = "22.04" ]; then
  sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
elif [ "${UBUNTU_RELEASE}" = "20.04" ]; then
  sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
elif [ "${UBUNTU_RELEASE}" = "18.04" ]; then
  sudo apt-get install -y python3.8 python3.8-venv python3.8-dev
else
  echo "ERROR: The Ubuntu version '${UBUNTU_RELEASE}' is outside the scope (18.04, 20.04 or 22.04)."
  lsb_release -a
  exit 1
fi

# Install curl
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install Qt
if [ "${UBUNTU_RELEASE}" = "22.04" ]; then
  sudo apt-get install -y qtbase5-dev qt5-qmake qtbase5-dev-tools qttools5-dev-tools
else
  sudo apt-get install -y qt5-default qt5-qmake qtbase5-dev-tools qttools5-dev-tools
fi

# Create the Python vEnv and install requirements
if [ "${UBUNTU_RELEASE}" = "22.04" ]; then
  /usr/bin/python3.10 -m venv pext-env
elif [ "${UBUNTU_RELEASE}" = "20.04" ]; then
  /usr/bin/python3.9 -m venv pext-env
elif [ "${UBUNTU_RELEASE}" = "18.04" ]; then
  /usr/bin/python3.8 -m venv pext-env
fi
source pext-env/bin/activate
pip install --upgrade pip
pip install tox-travis
pip install -r requirements.txt

# Generate translation
bash -xe prepare_activate_translations.sh 70 "https://hosted.weblate.org/exports/stats/pext/?format=json"
lrelease pext/pext.pro

# Run tests
source pext-env/bin/activate
if [ "${UBUNTU_RELEASE}" = "22.04" ]; then
  xvfb-run tox -v -e py310
elif [ "${UBUNTU_RELEASE}" = "20.04" ]; then
  xvfb-run tox -v -e py39
elif [ "${UBUNTU_RELEASE}" = "18.04" ]; then
  xvfb-run tox -v -e py38
fi

# Build the app
mkdir -p build-ubuntu-"${UBUNTU_RELEASE}"
cd build-ubuntu-"${UBUNTU_RELEASE}" || exit 1
bash -xve ../ci/build-app-image.sh
