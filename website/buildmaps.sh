#!/usr/bin/env bash

ROOTDIR=..
BUILDDIR=mapbuild
IMGDIR=mapimages
OUTDIR=src/img/generated

mkdir -p "$BUILDDIR" "$IMGDIR" "$OUTDIR"

echo "Generating basemap"
python3 "$ROOTDIR/geodata2basemap.py" --regions "$ROOTDIR/regions.json" --data "$ROOTDIR/geodata" --year 2020 --out "$BUILDDIR/2020_basemap.json"

echo "Building logo"
python3 "$ROOTDIR/genmapdata.py" --regions "$ROOTDIR/regions.json" --map "$ROOTDIR/maps/logo_nation.py" --base "$BUILDDIR/2020_basemap.json" --out "$BUILDDIR/2020_logo.json"
python3 "$ROOTDIR/mapdata2img.py" --directory "$IMGDIR" --mapfile "$BUILDDIR/2020_logo.json"
cp "$IMGDIR/nation-logo.svg" "$OUTDIR/logo.svg"

echo "Done."
