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
REPO_ROOT=$(readlink -f $(dirname $0))
OLD_CWD=$(readlink -f .)

pushd "$BUILD_DIR"

# install Miniconda, a self contained Python distribution, into AppDir
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p AppDir/usr -f

# activate Miniconda environment
. AppDir/usr/bin/activate

# install dependencies
git clone https://github.com/libgit2/libgit2
pushd libgit2; mkdir build/; cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr
make install DESTDIR="$BUILD_DIR"/AppDir -j$(nproc)
popd
pip install PyQt5==5.8 PyOpenGL PyOpenGL_accelerate
pip install -U pip
pip download pygit2; tar xf pygit2*.tar.gz; pushd pygit2*/
python setup.py build_ext --inplace --include-dirs="$BUILD_DIR"/AppDir/usr/include --library-dirs="$BUILD_DIR"/AppDir/usr/lib
python setup.py install
popd

# install Pext
(cd "$REPO_ROOT" && python setup.py install)


# copy resources to AppDir
cp "$REPO_ROOT"/pext.desktop "$REPO_ROOT"/pext/images/scalable/pext.svg AppDir
sed -i 's|Exec=.*|Exec=usr/bin/python usr/bin/pext|' AppDir/pext.desktop

# precompile bytecode to speed up startup
pushd AppDir
python -m compileall . -fqb || true
popd

# copy in libraries
wget https://raw.githubusercontent.com/AppImage/AppImages/master/functions.sh
(. functions.sh && cd AppDir && set +x && copy_deps && copy_deps && copy_deps && delete_blacklisted)

# remove unnecessary libraries and other useless data
pushd AppDir
find AppDir/usr/lib \
    -iname '*Tk*' \
    -or -iname '*QtNetwork*' \
    -or -iname '*lib2to3*' \
    -or -iname '*ucene*' \
    -or -iname '*pip*' \
    -or -iname '*setuptools*' \
    -or -iname '*declarative*  \
    -or -iname 'libkrb*.so*' \
    -or -iname 'libhcrypto*.so*' \
    -or -iname 'libheim*.so*' \
    -or -iname 'libroken*.so*' \
    -or -iname 'libreadline*.so*' \
    -delete
popd

# install AppRun
cat > AppDir/AppRun <<EAT
#! /bin/sh

export LD_LIBRARY_PATH="\$APPDIR"/usr/lib:"\$APPDIR"/usr/lib/x86_64-linux-gnu/
export PYTHONPATH="\$APPDIR"/usr/lib/python3.5:"\$APPDIR"/usr/lib/python3.5/site-packages/

exec "\$APPDIR"/usr/bin/python "\$APPDIR"/usr/bin/pext
EAT

chmod +x AppDir/AppRun

# get appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage --appimage-extract

# build AppImage
squashfs-root/AppRun AppDir

# move AppImage back to old CWD
mv Pext-*.AppImage* "$OLD_CWD"/
