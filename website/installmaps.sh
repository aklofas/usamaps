#!/usr/bin/env bash

IMGDIR=mapimages
OUTDIR=build/img

mkdir -p "$OUTDIR"

echo "Installing logo"
cp "$IMGDIR/nation-logo.svg" "$OUTDIR/logo.svg"
