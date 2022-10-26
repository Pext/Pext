#! /bin/bash

# use RAM disk if possible
if [ -d /dev/shm ]; then
    TEMP_BASE=/dev/shm
else
    TEMP_BASE=/tmp
fi

BUILD_DIR=$(mktemp -d "$TEMP_BASE/Pext-MacOS-build-XXXXXX")

cleanup () {
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
}

trap cleanup EXIT

OLD_CWD="$(pwd)"

# update version info (this will throw an error, but that's okay)
python3 setup.py || true

VERSION="$(head -n 1 "$OLD_CWD"/pext/VERSION)"

pushd "$BUILD_DIR"/ || exit 1

# install Miniconda, a self-contained Python distribution
wget https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh -b -p ~/miniconda -f
rm Miniconda3-latest-MacOSX-x86_64.sh 
export PATH="$HOME/miniconda/bin:$PATH"

# create conda env
conda create -n Pext python --yes
source activate Pext

# install dependencies
pip install -r "$OLD_CWD"/requirements.txt

# leave conda env
source deactivate

# create .app Framework
mkdir -p Pext.app/Contents/
mkdir Pext.app/Contents/MacOS Pext.app/Contents/Resources Pext.app/Contents/Resources/Pext
mv "$OLD_CWD"/Info.plist Pext.app/Contents/Info.plist

# copy Miniconda env
cp -R ~/miniconda/envs/Pext/* Pext.app/Contents/Resources/

# copy Pext
cp -R "$OLD_CWD"/* Pext.app/Contents/Resources/Pext/

# create entry script
cat > Pext.app/Contents/MacOS/Pext <<\EAT
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
EAT

if [ "$PEXT_BUILD_PORTABLE" -eq 1 ]; then
cat >> Pext.app/Contents/MacOS/Pext <<\EAT
  $DIR/../Resources/bin/python $DIR/../Resources/Pext/pext --portable $@
EAT
else
cat >> Pext.app/Contents/MacOS/Pext <<\EAT
  $DIR/../Resources/bin/python $DIR/../Resources/Pext/pext $@
EAT
fi

# make executable
chmod a+x Pext.app/Contents/MacOS/Pext

# remove bloat
pushd Pext.app/Contents/Resources || exit 1
rm -rf pkgs
find . -type d -iname '__pycache__' -print0 | xargs -0 rm -r
#find . -type f -iname '*.so*' -print -exec strip '{}' \;
rm -rf lib/cmake/
rm -rf share/{gtk-,}doc
rm lib/python3.7/site-packages/PyQt5/QtWebEngine* || true
rm -r lib/python3.7/site-packages/PyQt5/Qt/translations/qtwebengine* || true
rm lib/python3.7/site-packages/PyQt5/Qt/resources/qtwebengine* || true
rm -r lib/python3.7/site-packages/PyQt5/Qt/qml/QtWebEngine* || true
rm -r lib/python3.7/site-packages/PyQt5/Qt/plugins/webview/libqtwebview* || true
rm lib/python3.7/site-packages/PyQt5/Qt/libexec/QtWebEngineProcess* || true
rm lib/python3.7/site-packages/PyQt5/Qt/lib/libQt5WebEngine* || true
popd || exit 1
popd || exit 1

# generate .dmg
if [ "$PEXT_BUILD_PORTABLE" -eq 1 ]; then
  mv "$BUILD_DIR"/Pext.app Pext-portable-"${VERSION}".app
  zip -r Pext-portable-"${VERSION}".app.zip Pext-portable-*.app
else
  brew install create-dmg
  # "--skip-jenkins" is a temporary workaround for https://github.com/create-dmg/create-dmg/issues/72
  create-dmg --skip-jenkins --volname "Pext $VERSION" --volicon "$OLD_CWD"/pext/images/scalable/pext.icns \
  --window-pos 200 120 --window-size 800 400 --icon-size 100 --icon Pext.app 200 190 --hide-extension Pext.app \
  --app-drop-link 600 185 Pext-"${VERSION}".dmg "$BUILD_DIR"/
fi
