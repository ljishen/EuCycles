#!/usr/bin/env bash

set -eu

if [ "$#" -lt 2 ] || [[ "$1" == -* ]]; then
    cat <<-ENDOFMESSAGE
Usage: ./extract.sh SOURCE DEST CATEGORY
Extract information from SOURCE file and append to the DEST file.
ENDOFMESSAGE
    exit
fi

SOURCE="$1"
DEST="$2"
CATEGORY="${3:-}"

if [ ! -z "$CATEGORY" ]; then
    echo "$CATEGORY,Cycles," >> "$DEST"
    echo "$CATEGORY,Bitrate," >> "$DEST"
fi

# Extract cpu cycles
if ! cycles=$(grep -oP '\d+(?=\s+cycles)' "$SOURCE"); then
    echo "Error: no value for \"cycles\" in the source file."
    exit 1
fi

# Extract "bits_per_second" for receiver
if ! bitrate=$(grep -oP 'bits_per_second.+?\K[\d.]+' "$SOURCE" | tail -1); then
    echo "Error: no value (bitrate) for \"bits_per_second\" in the source file."
    exit 1
fi

num_lines=$(wc -l < "$DEST")

line_of_cycles=$(( num_lines - 1 ))
sed -i "$line_of_cycles s/$/${cycles},/" "$DEST"

line_of_bitrate=$(( num_lines ))
sed -i "$line_of_bitrate s/$/${bitrate},/" "$DEST"
