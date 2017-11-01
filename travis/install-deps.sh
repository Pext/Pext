#! /bin/bash

# install custom built libcurl system wide between git clone and test script
sudo apt-get purge -y curl\* libcurl\*

# install mbed TLS
sudo apt-get install -y libmbedtls-dev

# install cmake, which had a dependency on curl and was uninstalled in the previous step
wget https://cmake.org/files/v3.10/cmake-3.10.0-rc3-Linux-x86_64.tar.gz -O- | sudo tar xz -C /usr --strip-components=1

# the custom searches multiple locations for CA chains, and has everything but HTTP(S) disabled to remove the majority of dependencies
url=$(wget -qO- https://api.github.com/repos/curl/curl/releases/latest | grep tarball_url | cut -d'"' -f4)
wget "$url" -O- | tar xz
pushd curl*/
patch -p1 < "$TRAVIS_BUILD_DIR"/travis/curl-ssl-searchpaths.patch
mkdir build; cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DHTTP_ONLY=1 -DCMAKE_USE_MBEDTLS=1 -DBUILD_TESTING=0 -DCURL_CA_BUNDLE_SEARCHPATHS="/etc/ssl/ca-bundle.pem:/etc/ssl/certs/ca-certificates.crt:/etc/ssl/cert.pem:/etc/pki/tls/certs/ca-bundle.crt:/etc/pki/tls/cert.pem:/etc/pki/tls/cacert.pem:/usr/local/share/certs/ca-root-nss.crt"
sudo make install -j$(nproc)
popd

# build and install libgit2 from source, assuming that the latest version will also make pygit2 install without version errors
url=$(wget -qO- https://api.github.com/repos/libgit2/libgit2/releases/latest | grep tarball_url | cut -d'"' -f4)
wget "$url" -O- | tar xz
pushd libgit2*/; mkdir build/; cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr
sudo make install -j$(nproc)
popd
