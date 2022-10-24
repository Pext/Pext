#! /bin/bash

PYTHON_VERSION="${1}"
echo "PYTHON_VERSION: ${PYTHON_VERSION}"
echo "PYTHON_VERSION without dot: ${PYTHON_VERSION//./}"
UBUNTU_RELEASE=$(sudo lsb_release -rs)
echo "UBUNTU_RELEASE: ${UBUNTU_RELEASE}"

# Update APT repositories
sudo apt-get update

# Update pip
whereis python3
python3 --version
python3 -m pip --version
python3 -m pip install --user --upgrade pip
python3 -m pip --version

# Install vEnv
#sudo apt-get install -y python"${PYTHON_VERSION}" python"${PYTHON_VERSION}"-venv python"${PYTHON_VERSION}"-dev
python3 -m pip install --user virtualenv
python3 -m pip list
#sudo apt search "*python${PYTHON_VERSION}*"

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
whereis python3
python3 --version
python3 -m pip --version
python3 -m pip install --upgrade pip
python3 -m pip --version

# Install Tox Travis
#pip install tox-travis
python3 -m pip install tox-travis
python3 -m pip list

# Install requirements
#pip install -r requirements.txt
python3 -m pip install -r requirements.txt
python3 -m pip list

# Generate translation
bash -xe prepare_activate_translations.sh 70 "https://hosted.weblate.org/exports/stats/pext/?format=json"
lrelease pext/pext.pro

# Run tests
source pext-env/bin/activate
xvfb-run tox -v -e py"${PYTHON_VERSION//./}"

# Build the app
rm -fR build
mkdir -p build
cd build || exit 1
bash -xve ../ci/build-app-image.sh
