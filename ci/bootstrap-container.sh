#! /bin/bash

set -xv

echo "###########################################"
sudo lsb_release -a
echo "###########################################"
sudo cat /etc/os-release
echo "###########################################"
sudo cat /etc/issue
echo "###########################################"
sudo hostnamectl
echo "###########################################"
# VERSION="18.04.6 LTS (Bionic Beaver)"
# VERSION_CODENAME=bionic
# UBUNTU_CODENAME=bionic
exit 128

# install Python 3.6
#sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3.6 python3.6-venv python3.6-dev
#sudo apt-get install -y python3.6 python3.6-venv python3.6-dev

# install proper cross-distro libcurl
#echo 'deb [trusted=yes] https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/ /' | sudo tee /etc/apt/sources.list.d/curl-httponly.list
#echo "###########################################"
##wget https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O- && sudo apt-key add -
#echo "###########################################"
#wget -nv https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key -O Release.key
#echo "###########################################"
#ls -lhaR /etc/apt/sources.list.d/
#echo "###########################################"
#sudo cat /etc/apt/sources.list.d/curl-httponly.list
#sudo cat /etc/apt/sources.list.d/git-core-ubuntu-ppa-bionic.list
#sudo cat /etc/apt/sources.list.d/git-core-ubuntu-ppa-bionic.list.save
#sudo cat /etc/apt/sources.list.d/github_git-lfs.list.save
#sudo cat /etc/apt/sources.list.d/microsoft-prod.list
#sudo cat /etc/apt/sources.list.d/microsoft-prod.list.save
#sudo cat /etc/apt/sources.list.d/ondrej-ubuntu-php-bionic.list
#sudo cat /etc/apt/sources.list.d/ubuntu-toolchain-r-ubuntu-test-bionic.list
#sudo cat /etc/apt/sources.list.d/ubuntu-toolchain-r-ubuntu-test-bionic.list.save
#echo "###########################################"
##sudo apt-key add - < Release.key
##sudo apt-key add Release.key
##sudo apt-key add - < Release.key
#sudo apt-key adv --fetch-keys https://download.opensuse.org/repositories/home:/TheAssassin:/AppImageLibraries/xUbuntu_18.04/Release.key --recv-keys 662394A9577D6015
#echo "${?}"
##sudo apt-key adv --keyserver keyserver.opensuse.org --recv-keys 662394A9577D6015
#echo "###########################################"
#sudo apt-key list
##sudo apt-key list | grep -A 1 expired
#echo "###########################################"
#sudo rm -f Release.key
#echo "###########################################"
#sudo apt-get update
echo "###########################################"
sudo apt list --installed | grep -i curl
echo "###########################################"
#sudo apt-get install -y curl libcurl4-gnutls-dev libcurl3-gnutls libcurl3 bc
sudo apt-get install -y libcurl4-gnutls-dev libcurl3 bc
echo "###########################################"
sudo apt list --installed | grep -i curl
echo "###########################################"

# install somewhat up-to-date Qt
sudo add-apt-repository -y ppa:beineri/opt-qt-5.14.2-bionic
sudo apt-get update
sudo apt-get install -y qt514tools
