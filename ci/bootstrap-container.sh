#! /bin/bash

# Install Python 3.8
sudo apt-get update
sudo apt-get install python3.8 python3.8-venv python3.8-dev


# Install proper cross-distro libcurl
#echo 'deb [trusted=yes] https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/ /' | sudo tee /etc/apt/sources.list.d/curl-httponly.list
##wget -nv https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O Release.key
##sudo apt-key add - < Release.key
##sudo apt-key add Release.key
##sudo apt-key add - < Release.key
#sudo apt-key adv --fetch-keys https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key --recv-keys 662394A9577D6015
#echo "${?}"
#sudo apt-get update
##sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3 bc
sudo apt-get install -y curl libcurl4 libcurl4-gnutls-dev bc

# Install somewhat up-to-date Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-bionic
sudo apt-get update
sudo apt-get install -y qt514tools

# Create the Python vEnv and install requirements
/usr/bin/python3.8 -m venv pext-env
source pext-env/bin/activate
pip install --upgrade pip
pip install tox-travis
pip install -r requirements.txt
