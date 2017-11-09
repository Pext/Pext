#! /bin/bash

# install proper cross-distro libcurl
sudo sh -c "echo 'deb http://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_14.04/ /' > /etc/apt/sources.list.d/curl-httponly.list"
wget -nv https://download.opensuse.org/repositories/home:TheAssassin:AppImageLibraries/xUbuntu_14.04/Release.key -O- | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y curl-httponly libcurl3-httponly

# install additional libraries
sudo apt-get install -y libgit2
