#!/bin/bash

# Create a directory for compressed files if it doesn't exist
mkdir -p compressed_files

# Function to compress and split files
compress_and_split() {
    local file=$1
    local basename=$(basename "$file")
    echo "Processing $basename..."
    tar czf - "$file" | split -b 39M - "compressed_files/${basename}.tar.gz.part"
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
        compress_and_split "$file"
    else
        echo "File $file not found"
    fi
done

echo "All files have been processed. Check the 'compressed_files' directory."
