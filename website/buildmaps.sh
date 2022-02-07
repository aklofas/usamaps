#!/usr/bin/env bash

BUILDDIR=mapbuild

echo "Generating basemap"
mkdir -p "$BUILDDIR"
python3 ../geodata2basemap.py -d ../geodata -r ../regions.json -y 2020 -o "$BUILDDIR/2020_basemap.json"


echo "Done."
