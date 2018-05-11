#! /bin/bash

set -x
set -e

# use RAM disk if possible
if [ -d /dev/shm ]; then
    TEMP_BASE=/dev/shm
else
    TEMP_BASE=/tmp
fi

BUILD_DIR=$(mktemp -d -p "$TEMP_BASE" Pext-AppImage-build-XXXXXX)

cleanup () {
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
}

trap cleanup EXIT

# store repo root as variable
REPO_ROOT=$(readlink -f $(dirname $(dirname "$0")))
OLD_CWD=$(readlink -f .)

pushd "$BUILD_DIR"/

# install Miniconda, a self contained Python distribution, into AppDir
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p AppDir/usr -f

# activate Miniconda environment
. AppDir/usr/bin/activate

# build AppImageUpdate and install it into conda prefix
git clone --recursive https://github.com/AppImage/AppImageUpdate
pushd AppImageUpdate
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$CONDA_PREFIX"/ -DBUILD_QT_UI=OFF
make -j$(nproc)
make install
popd

# Put all appimageupdatetool deps in our AppImage
AIUT_DIR=$(mktemp -d -p "$TEMP_BASE" AppImageUpdateTool-XXXXXX)
pushd "$AIUT_DIR"/
url=$(wget -qO- https://api.github.com/repos/AppImage/AppImageUpdate/releases | grep browser_download_url | cut -d: -f2- | sed 's|"||g' | grep appimageupdatetool | grep -E '.AppImage$' | sed 's| ||g')
wget "$url"
chmod +x appimageupdatetool*.AppImage
./appimageupdatetool*.AppImage --appimage-extract
rm squashfs-root/usr/lib/libappimageupdate.so
cp squashfs-root/usr/lib/*.so* "$CONDA_PREFIX"/lib/
popd

# install python-appimageupdate into conda prefix
git clone https://github.com/TheAssassin/python-appimageupdate.git
pushd python-appimageupdate
python setup.py install --prefix="$CONDA_PREFIX/"
popd

# Arch lacks libxi, which is needed for xcb support (aka: X11)
conda config --add channels conda-forge
conda install -y xorg-libxi

# install dependencies
pip install PyQt5==5.8 PyOpenGL PyOpenGL_accelerate dulwich

# install Pext
pushd "$REPO_ROOT"/
python setup.py install
popd

# copy resources to AppDir
mkdir -p AppDir/usr/share/metainfo
cp "$REPO_ROOT"/pext.appdata.xml AppDir/usr/share/metainfo
cp "$REPO_ROOT"/pext.desktop "$REPO_ROOT"/pext/images/scalable/pext.svg AppDir

# copy in libraries
wget https://raw.githubusercontent.com/AppImage/AppImages/master/functions.sh
# back up conda provided libraries -- system one won't work
mkdir lib-bak
cp AppDir/usr/lib/*.so* lib-bak/
#(. functions.sh && cd AppDir && set +x && copy_deps && copy_deps && copy_deps && move_lib && delete_blacklisted)
(. functions.sh && cd AppDir && set +x && move_lib || true && delete_blacklisted)
mv AppDir/usr/lib/x86_64-linux-gnu/*.so* AppDir/usr/lib/ || true
# copy back libraries
cp --remove-destination lib-bak/* AppDir/usr/lib/
#rm -rf AppDir/usr/lib/x86_64-linux-gnu/

# remove unnecessary libraries and other useless data
find AppDir/usr \
    -iname '*Tk*' \
    -or -iname '*QtNetwork*' \
    -or -iname '*lib2to3*' \
    -or -iname '*ucene*' \
    -or -iname '*pip*' \
    -or -iname '*setuptools*' \
    -or -iname '*declarative*'  \
    -or -iname 'libreadline*.so*' \
    -or -iname '*.a' \
    -delete

# precompile bytecode to speed up startup
# do this after deleting lib2to3, otherwise it won't compile
pushd AppDir/
python -m compileall . -fqb || true
popd

# install AppRun
cat > AppDir/AppRun <<EAT
#! /bin/sh

# make sure to set APPDIR when run directly from the AppDir
if [ -z \$APPDIR ]; then APPDIR=\$(readlink -f \$(dirname "\$0")); fi

export LD_LIBRARY_PATH="\$APPDIR"/usr/lib

for path in /etc/ssl/ca-bundle.pem \\
    /etc/ssl/certs/ca-certificates.crt \\
    /etc/ssl/cert.pem /etc/pki/tls/certs/ca-bundle.crt \\
    /etc/pki/tls/cert.pem /etc/pki/tls/cacert.pem \\
    /usr/local/share/certs/ca-root-nss.crt; do
    if [ -f "\$path" ]; then
        export SSL_CERT_FILE="\$path"
        break
    fi
done

exec "\$APPDIR"/usr/bin/python -m pext "\$@"
EAT

chmod +x AppDir/AppRun

# get appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage --appimage-extract

# build AppImage

# continuous releases should use the latest continuous build for updates
APPIMAGEUPDATE_TAG=continuous

# if building for a tag, embed "latest" to make AppImageUpdate use the latest tag on updates
# you could call it the "stable" channel
if [ "$TRAVIS_TAG" != "" ]; then
    APPIMAGEUPDATE_TAG=latest
fi

squashfs-root/AppRun -u "gh-releases-zsync|Pext|Pext|$APPIMAGEUPDATE_TAG|Pext*x86_64.AppImage.zsync" AppDir

# move AppImage back to old CWD
mv Pext-*.AppImage* "$OLD_CWD"/
