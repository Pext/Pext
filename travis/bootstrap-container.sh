#! /bin/bash

# appimageupdate deps
sudo apt-get update
sudo apt-get install desktop-files-utils

# install Python 3.6
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.6

# install proper cross-distro libcurl
sudo sh -c "echo 'deb http://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_14.04/ /' > /etc/apt/sources.list.d/curl-httponly.list"
wget https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_14.04/Release.key -O- | sudo apt-key add -
sudo apt-get update

sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3
