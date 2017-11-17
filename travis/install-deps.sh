#! /bin/bash

# install proper cross-distro libcurl
sudo sh -c "echo 'deb http://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_14.04/ /' > /etc/apt/sources.list.d/curl-httponly.list"
wget -nv https://download.opensuse.org/repositories/home:TheAssassin:AppImageLibraries/xUbuntu_14.04/Release.key -O- | sudo apt-key add -
sudo apt-get update

sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3

# update CMake
wget https://cmake.org/files/v3.10/cmake-3.10.0-rc3-Linux-x86_64.tar.gz -O- | sudo tar xz -C /usr --strip-components=1

# install additional libraries
sudo apt-get install -y libgit2-dev

# fix setup.py's pygit2 version
pygit2_version=$(dpkg -l | grep libgit2-dev | awk '{print $3}' | cut -d- -f1)
sed "s|'pygit2'|'pygit2==$pygit2_version'|" setup.py
