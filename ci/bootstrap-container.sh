#! /bin/bash

set -xv

# install Python 3.6
#sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.6
#sudo apt-get install -y python3.6 python3.6-venv python3.6-dev

# install proper cross-distro libcurl
sudo sh -c "echo 'deb https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/ /' > /etc/apt/sources.list.d/curl-httponly.list"
echo "###########################################"
#wget https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O- && sudo apt-key add -
echo "###########################################"
wget -nv https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O Release.key
echo "###########################################"
ls -lhaR /etc/apt/sources.list.d/
echo "###########################################"
cat /etc/apt/sources.list.d/curl-httponly.list
#sudo apt-key add - < Release.key
echo "###########################################"
sudo apt-key add Release.key
echo "###########################################"
sudo rm -f Release.key
echo "###########################################"
sudo apt-get update
echo "###########################################"

sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3 bc

# install somewhat up-to-date Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-xenial
sudo apt-get update
sudo apt-get install -y qt514tools
