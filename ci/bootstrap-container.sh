#! /bin/bash

UBUNTU_CODENAME=$(sudo lsb_release -cs)
UBUNTU_RELEASE=$(sudo lsb_release -rs)

# Install Python
sudo apt-get update
echo "######################################"
sudo apt search qt5
exit 1
echo "######################################"
sudo python --version
echo "######################################"
python --version
echo "######################################"
if [ "${UBUNTU_CODENAME}" = "jammy" ]; then
  sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
elif [ "${UBUNTU_CODENAME}" = "focal" ]; then
  sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
elif [ "${UBUNTU_CODENAME}" = "bionic" ]; then
  sudo apt-get install -y python3.8 python3.8-venv python3.8-dev
else
  echo "ERROR: The Ubuntu version '${UBUNTU_CODENAME}' is outside the scope (bionic, focal or jammy)."
  sudo lsb_release -a
  exit 1
fi

# Install curl
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install Qt
if [ "${UBUNTU_CODENAME}" = "jammy" ]; then
  sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-jammy
elif [ "${UBUNTU_CODENAME}" = "focal" ]; then
  sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-focal
elif [ "${UBUNTU_CODENAME}" = "bionic" ]; then
  sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-bionic
fi
sudo apt-get update
sudo apt-get install -y qt514tools

# Create the Python vEnv and install requirements
if [ "${UBUNTU_CODENAME}" = "jammy" ]; then
  /usr/bin/python3.10 -m venv pext-env
elif [ "${UBUNTU_CODENAME}" = "focal" ]; then
  /usr/bin/python3.9 -m venv pext-env
elif [ "${UBUNTU_CODENAME}" = "bionic" ]; then
  /usr/bin/python3.8 -m venv pext-env
fi
source pext-env/bin/activate
pip install --upgrade pip
pip install tox-travis
pip install -r requirements.txt

# Generate translation
source /opt/qt514/bin/qt514-env.sh || true
bash -xe prepare_activate_translations.sh 70 "https://hosted.weblate.org/exports/stats/pext/?format=json"
lrelease pext/pext.pro

# Run tests
source pext-env/bin/activate
if [ "${UBUNTU_CODENAME}" = "jammy" ]; then
  xvfb-run tox -v -e py310
elif [ "${UBUNTU_CODENAME}" = "focal" ]; then
  xvfb-run tox -v -e py39
elif [ "${UBUNTU_CODENAME}" = "bionic" ]; then
  xvfb-run tox -v -e py38
fi

# Build the app
mkdir -p build
cd build && exit 1
pwd
ls -lha
pwd
ls -lha ../
bash -xe ../ci/build-appimage.sh
