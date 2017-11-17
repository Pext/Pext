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
bash Miniconda3-latest-Linux-x86_64.sh -b -p AppDir/miniconda -f

# activate Miniconda environment
. AppDir/miniconda/bin/activate

# install dependencies
pygit2_version=$(dpkg -l | grep libgit2-dev | awk '{print $3}' | cut -d- -f1)
pip install PyQt5==5.8 PyOpenGL PyOpenGL_accelerate pygit2=="$pygit2_version"

# install Pext
pushd "$REPO_ROOT"/
python setup.py install
popd

# copy resources to AppDir
cp "$REPO_ROOT"/pext.desktop "$REPO_ROOT"/pext/images/scalable/pext.svg AppDir
sed -i 's|Exec=.*|Exec=usr/bin/python usr/bin/pext|' AppDir/pext.desktop

# copy in libraries
wget https://raw.githubusercontent.com/AppImage/AppImages/master/functions.sh
(. functions.sh && cd AppDir && set +x && copy_deps && copy_deps && copy_deps && move_lib && delete_blacklisted)
find AppDir/usr/lib/x86_64-linux-gnu/ -iname '*libssl*.so*'  -delete
mv AppDir/usr/lib/x86_64-linux-gnu/*.so* AppDir/usr/lib/
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

# TODO: for debugging only
cp $(which curl) AppDir/usr/bin

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

exec "\$APPDIR"/miniconda/bin/python -m pext "\$@"
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
