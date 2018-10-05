#! /bin/bash

set -x
set -e

# use RAM disk if possible
if [ -d /dev/shm ] && [ "$CI" != "" ]; then
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

# set up custom AppRun script
cat > AppRun.sh <<\EAT
#! /bin/sh

# make sure to set APPDIR when run directly from the AppDir
if [ -z $APPDIR ]; then APPDIR=$(readlink -f $(dirname "$0")); fi

export LD_LIBRARY_PATH="$APPDIR"/usr/lib

for path in /etc/ssl/ca-bundle.pem \
    /etc/ssl/certs/ca-certificates.crt \
    /etc/ssl/cert.pem /etc/pki/tls/certs/ca-bundle.crt \
    /etc/pki/tls/cert.pem /etc/pki/tls/cacert.pem \
    /usr/local/share/certs/ca-root-nss.crt; do
    if [ -f "$path" ]; then
        export SSL_CERT_FILE="$path"
        break
    fi
done

exec "$APPDIR"/usr/bin/python -m pext "$@"
EAT

chmod +x AppRun.sh

# get linuxdeploy and its conda plugin
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
wget https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/master/linuxdeploy-plugin-conda.sh

# can use the plugin's environment variables to ease some setup
export CONDA_CHANNELS=conda-forge
export CONDA_PACKAGES=xorg-libxi
export PIP_REQUIREMENTS="PyQt5 PyOpenGL PyOpenGL_accelerate dulwich pynput requests ."
export VERSION=$(cat "$REPO_ROOT/pext/VERSION")

mkdir -p AppDir/usr/share/metainfo/
cp "$REPO_ROOT"/*.appdata.xml AppDir/usr/share/metainfo/

# continuous releases should use the latest continuous build for updates
APPIMAGEUPDATE_TAG=continuous

# if building for a tag, embed "latest" to make AppImageUpdate use the latest tag on updates
# you could call it the "stable" channel
if [ "$TRAVIS_TAG" != "" ]; then
    APPIMAGEUPDATE_TAG=latest
fi

export UPD_INFO="gh-releases-zsync|Pext|Pext|$APPIMAGEUPDATE_TAG|Pext*x86_64.AppImage.zsync"

chmod +x linuxdeploy*.{sh,AppImage}

# make sure linuxdeploy-plugin-conda switches to repo root so that the "." pip requirement can be satisfied
export PIP_WORKDIR="$REPO_ROOT"

# build AppDir using linuxdeploy
# NO_CLEANUP makes more efficient
env NO_CLEANUP=1 ./linuxdeploy-x86_64.AppImage --appdir AppDir --plugin conda -d "$REPO_ROOT"/io.pext.pext.desktop -i "$REPO_ROOT"/pext/images/scalable/pext.svg --custom-apprun AppRun.sh -v0

# remove unused files from AppDir manually
# these files are nothing the conda plugin could remove manually
rm  AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/QtWebEngine*
rm -r AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/translations/qtwebengine*
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/resources/qtwebengine*
rm -r AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/qml/QtWebEngine*
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/plugins/webview/libqtwebview*
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/libexec/QtWebEngineProcess*
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/lib/libQt5WebEngine*

# now, actually build AppImage
# the extracted AppImage files will be cleaned up now
./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

# move AppImage back to old CWD
mv Pext*.AppImage* "$OLD_CWD"/
