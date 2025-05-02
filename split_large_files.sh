#!/bin/bash

# Function to compress file with zip and split
compress_with_zip() {
    local file=$1
    local dir=$(dirname "$file")
    local basename=$(basename "$file")
    echo "Processing $basename..."
    cd "$dir"
    zip -s 40m "${basename}.zip" "$basename"
    cd - > /dev/null
    echo "Finished processing $basename"
}

# List of files to compress
files=(
    "./data/sintetic/dataset_fishing_train.csv"
    "./data/sintetic/list_encounters_3meses.pickle"
    "./data/sintetic/gdf_sintetic2.pkl"
    "./data/sintetic/gdf_sintetic.pkl"
    "./data/sintetic/gdf_loitering_trajs.pkl"
    "./data/gadm41_BRA.gpkg"
    "./data/train_behaviors/fishing_and_nofishing/dataset_fishing_train.csv"
    "./data/sistram/gdf_sistram_1dn_lrit.pkl"
    "./data/sistram/gdf_sistram_1dn_ais_ihs.pkl"
    "./metamodel.db"
    "./encounters.html"
)

# Process each file
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        compress_with_zip "$file"
    else
        echo "File $file not found"
    fi
done

echo "All files have been processed. Check for .zip and .z* files in the original directories."
