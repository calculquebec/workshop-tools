#!/bin/bash

URL_FILE="$1"

if [ -z "$URL_FILE" ] ; then
  echo Usage: $0 'https://full/URL/to/file.zip'
  exit 1
fi

ZIP_FILE=$(basename $URL_FILE)
MATERIAL="${ZIP_FILE%.zip}"

SHARED_DIR=$(dirname $0)
cd "$SHARED_DIR"

if [ ! -f "$ZIP_FILE" ]; then
  wget "$URL_FILE" -O "$ZIP_FILE"
  chmod 640 "$ZIP_FILE"
fi

if [ ! -d "$MATERIAL" ]; then
  unzip -o "$ZIP_FILE"
  chmod -R g+rX "$MATERIAL"
fi

mkdir -p "$HOME/$MATERIAL"
rsync -av "$SHARED_DIR/$MATERIAL/" "$HOME/$MATERIAL/"
