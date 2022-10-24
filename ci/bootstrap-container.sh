#! /bin/bash

UBUNTU_CODENAME=$(sudo lsb_release -cs)

# Install Python
sudo apt-get update
echo "###################################################"
sudo apt search venv
echo "###################################################"
sudo apt search python3.
echo "###################################################"
echo "UBUNTU_CODENAME: ${UBUNTU_CODENAME}"
if [ "${UBUNTU_CODENAME}" -eq jammy ]; then
  sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
elif [ "${UBUNTU_CODENAME}" -eq focal ]; then
  sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
elif [ "${UBUNTU_CODENAME}" -eq bionic ]; then
  sudo apt-get install -y python3.8 python3.8-venv python3.8-dev
else
  echo "ERROR: The Ubuntu version '${UBUNTU_CODENAME}' is outside the scope (bionic, focal or jammy)."
  sudo lsb_release -a
  exit 1
fi

# Install curl
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-bionic
sudo apt-get update
sudo apt-get install -y qt514tools

# Create the Python vEnv and install requirements
if [ "${UBUNTU_CODENAME}" -eq jammy ]; then
  /usr/bin/python3.10 -m venv pext-env
elif [ "${UBUNTU_CODENAME}" -eq focal ]; then
  /usr/bin/python3.9 -m venv pext-env
elif [ "${UBUNTU_CODENAME}" -eq bionic ]; then
  /usr/bin/python3.8 -m venv pext-env
fi
source pext-env/bin/activate
pip install --upgrade pip
pip install tox-travis
pip install -r requirements.txt
