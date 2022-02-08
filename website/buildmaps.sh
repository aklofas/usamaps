#!/usr/bin/env bash

ROOTDIR=..
BUILDDIR=mapbuild
#IMGDIR=mapimages
OUTICON=src/_includes/usericons/generated
OUTIMG=src/_includes/generated

mkdir -p "$BUILDDIR" "$OUTICON" "$OUTIMG"

echo "Generating basemap"
python3 "$ROOTDIR/geodata2basemap.py" --regions "$ROOTDIR/regions.json" --data "$ROOTDIR/geodata" --year 2020 --out "$BUILDDIR/2020_basemap.json"

echo "Building logo"
python3 "$ROOTDIR/genmapdata.py" --regions "$ROOTDIR/regions.json" --map "$ROOTDIR/maps/logo_nation.py" --base "$BUILDDIR/2020_basemap.json" --out "$BUILDDIR/2020_logo.json"
python3 "$ROOTDIR/mapdata2img.py" --mapfile "$BUILDDIR/2020_logo.json" --directory "$OUTICON"
#cp "$IMGDIR/nation-logo.svg" "$OUTICON/logo.svg"

echo "Build basic nation"
python3 "$ROOTDIR/genmapdata.py" --regions "$ROOTDIR/regions.json" --map "$ROOTDIR/maps/basic_nation.py" --base "$BUILDDIR/2020_basemap.json" --out "$BUILDDIR/2020_nation.json"
python3 "$ROOTDIR/mapdata2img.py" --mapfile "$BUILDDIR/2020_nation.json" --directory "$OUTIMG"
#cp "$IMGDIR/nation-logo.svg" "$OUTICON/logo.svg"

echo "Done."
