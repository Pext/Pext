#! /bin/bash

echo "##################################################"
sudo echo "$VERSION" || true
echo "##################################################"
sudo . /etc/os-release; echo "${VERSION/*, /}" || true
echo "##################################################"
sudo . /etc/os-release
read _ UBUNTU_VERSION_NAME <<< "$VERSION"
echo "$UBUNTU_VERSION_NAME"
echo "##################################################"
sudo cat /etc/os-release | grep UBUNTU_CODENAME | cut -d = -f 2
echo "##################################################"
sudo lsb_release -cs
echo "##################################################"
sudo lsb_release -a || true
echo "##################################################"
sudo cat /etc/os-release || true
echo "##################################################"
sudo cat /etc/issue || true
echo "##################################################"
sudo hostnamectl || true
echo "##################################################"

# Install Python
sudo apt-get update
echo "###################################################"
sudo apt search venv
echo "###################################################"
sudo apt search python3.
echo "###################################################"
sudo apt-get install -y python3.8 python3.8-venv python3.8-dev

# Install curl
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-bionic
sudo apt-get update
sudo apt-get install -y qt514tools

# Create the Python vEnv and install requirements
/usr/bin/python3.8 -m venv pext-env
source pext-env/bin/activate
pip install --upgrade pip
pip install tox-travis
pip install -r requirements.txt
