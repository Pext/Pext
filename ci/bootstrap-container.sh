#! /bin/bash

set -xv

# install Python 3.6
#sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.6
#sudo apt-get install -y python3.6 python3.6-venv python3.6-dev

# install proper cross-distro libcurl
ls -lha .
sudo sh -c "echo 'deb http://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/ /' > /etc/apt/sources.list.d/curl-httponly.list"
#wget https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O- && sudo apt-key add -
wget -nv https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O Release.key
ls -lha .
#sudo apt-key add - < Release.key
sudo cat Release.key | sudo apt-key add -
sudo apt-get update

sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3 bc

# install somewhat up-to-date Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-xenial
sudo apt-get update
sudo apt-get install -y qt514tools
