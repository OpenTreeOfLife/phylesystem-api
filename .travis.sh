#!/bin/sh

# The code below was lovingly borrowed from:
# https://raw.github.com/libgit2/pygit2/master/.travis.sh

cd ~

git clone --depth=1 -b master https://github.com/libgit2/libgit2.git
cd libgit2/

mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=../_install -DBUILD_CLAR=OFF
cmake --build . --target install

ls -la ..
