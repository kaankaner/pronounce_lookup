#!bin/bash

INSTALL_DIR=/usr/local/bin
BINARY=$INSTALL_DIR/pronounce-lookup

cp src/pronounce-lookup.py $BINARY
chmod 0775 $BINARY

