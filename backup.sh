#!/bin/sh

script_dir=$(dirname "$0")

cd "$script_dir"

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

new_dir="$script_dir/backup/$timestamp"
data_dir="$script_dir/static"

mkdir -p "$new_dir"

cp -r "$data_dir/." "$new_dir"

cp figma_screens_tr.json "$new_dir"
cp figma_screens_tt.json "$new_dir"

# find $data_dir -type f -name "*.png" -exec rm -f {} \;
# find $data_dir -type f -name "*.png"
find $data_dir -type f ! -name 'styles.css' -exec rm -f {} \;
find $data_dir -mindepth 1 -type d -empty -delete
