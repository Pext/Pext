#! /bin/bash

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
REPO_ROOT="$(readlink -f $(dirname $(dirname "$0")))"
OLD_CWD="$(readlink -f .)"

pushd "${BUILD_DIR}"/ || exit 1

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

EAT

if [ "$PEXT_BUILD_PORTABLE" -eq 1 ]; then
cat >> AppRun.sh <<\EAT
  exec "$APPDIR"/usr/bin/python -m pext --portable "$@"
EAT
else
cat >> AppRun.sh <<\EAT
  exec "$APPDIR"/usr/bin/python -m pext "$@"
EAT
fi

chmod +x AppRun.sh

# get linuxdeploy and its conda plugin
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
wget https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/e714783a1ca6fffeeb9dd15bbfce83831bb196f8/linuxdeploy-plugin-conda.sh  # We use an older linuxdeploy-plugin-conda because commit 76c8c8bf4e7dd435eda9c9a1de88a980c697f58f breaks the Pext build

# Don't remove include, needed for compiling some extensions
sed -i 's;rm -rf include/;;g' linuxdeploy-plugin-conda.sh

# Don't remove setuptools, needed for some packages modules may need (https://github.com/Pext/Pext/issues/291)
sed -i 's;rm -rf lib/python?.?/site-packages/setuptools;;g' linuxdeploy-plugin-conda.sh

# can use the plugin's environment variables to ease some setup
export CONDA_CHANNELS=conda-forge
export CONDA_PACKAGES=xorg-libxi
export PIP_REQUIREMENTS="."

mkdir -p AppDir/usr/share/metainfo/
cp "$REPO_ROOT"/*.appdata.xml AppDir/usr/share/metainfo/

# continuous releases should use the latest continuous build for updates
APPIMAGEUPDATE_TAG=continuous

# if building for a tag, embed "latest" to make AppImageUpdate use the latest tag on updates
# you could call it the "stable" channel
if [ "$TRAVIS_TAG" != "" ]; then
    APPIMAGEUPDATE_TAG=latest
fi

if [ "$PEXT_BUILD_PORTABLE" -eq 1 ]; then
  export UPD_INFO="gh-releases-zsync|Pext|Pext|$APPIMAGEUPDATE_TAG|Pext-portable-*x86_64.AppImage.zsync"
else
  export UPD_INFO="gh-releases-zsync|Pext|Pext|$APPIMAGEUPDATE_TAG|Pext*x86_64.AppImage.zsync"
fi

chmod +x linuxdeploy*.{sh,AppImage}

# make sure linuxdeploy-plugin-conda switches to repo root so that the "." pip requirement can be satisfied
export PIP_WORKDIR="$REPO_ROOT"
export PIP_VERBOSE=1

./linuxdeploy-x86_64.AppImage --appdir AppDir --plugin conda -d "$REPO_ROOT"/io.pext.pext.desktop -i "$REPO_ROOT"/pext/images/scalable/pext.svg --custom-apprun AppRun.sh

# remove unused files from AppDir manually
# these files are nothing the conda plugin could remove manually
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/QtWebEngine* || true
rm -r AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/translations/qtwebengine* || true
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/resources/qtwebengine* || true
rm -r AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/qml/QtWebEngine* || true
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/plugins/webview/libqtwebview* || true
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/libexec/QtWebEngineProcess* || true
rm AppDir/usr/conda/lib/python3.6/site-packages/PyQt5/Qt/lib/libQt5WebEngine* || true

# now, actually build AppImage
# the extracted AppImage files will be cleaned up now
#./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

ls -al AppDir/

python "$REPO_ROOT/setup.py" || true
if [ "$PEXT_BUILD_PORTABLE" -eq 1 ]; then
  VERSION=portable-$(cat "$REPO_ROOT/pext/VERSION")
else
  VERSION=$(cat "$REPO_ROOT/pext/VERSION")
fi
export VERSION

wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool*.AppImage
./appimagetool*.AppImage AppDir -u "$UPD_INFO"

# Print version to test if the AppImage runs at all
chmod +x Pext*.AppImage*
xvfb-run ./Pext*.AppImage* --version

# move AppImage back to old CWD
sudo mv Pext*.AppImage* "$OLD_CWD"/
