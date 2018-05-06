#!/usr/bin/env bash

set -eu

if [ "$#" -lt 3 ] || [[ "$1" == -* ]]; then
    cat <<-ENDOFMESSAGE
Usage: ./extract2csv.sh SOURCE DEST CATEGORY
Extract information from SOURCE file and append it to the DEST file based on the CATEGORY.

Format of CATEGORY: bytes,num_servs, e.g. 1K,1 2G,2
ENDOFMESSAGE
    exit
fi

SOURCE="$1"
DEST="$2"
CATEGORY="$3"

# Extract cpu cycles
if ! cycles=$(grep -oP '\d+(?=\s+cycles)' "$SOURCE"); then
    echo "Error: no value for \"cycles\" in the source file."
    exit 1
fi

# Extract the average bandwidth "bit/s" on the client side
if ! bitrate=$(grep -oP 'SUMMARY.+bitrate: \K[\d.]+' "$SOURCE"); then
    echo "Error: no value (bitrate) for \"[SUMMARY] ... bitrate: \" in the source file."
    exit 1
fi

category_line_num=$(grep -n "$CATEGORY" "$DEST" | head -n 1 | cut -d ':' -f 1)

if [ -z "$category_line_num" ]; then
    echo "$CATEGORY,Cycles," >> "$DEST"
    echo "$CATEGORY,Bitrate," >> "$DEST"
    category_line_num=$(grep -n "$CATEGORY" "$DEST" | head -n 1 | cut -d ':' -f 1)
fi

line_of_cycles=$(( category_line_num ))
sed -i "$line_of_cycles s/$/${cycles},/" "$DEST"

line_of_bitrate=$(( category_line_num + 1 ))
sed -i "$line_of_bitrate s/$/${bitrate},/" "$DEST"
