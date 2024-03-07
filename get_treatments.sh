#!/bin/bash

# Check if both start and end parameters are provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <start> <end>"
  exit 1
fi

# Assign the provided parameters to variables
start=$1
end=$2

# Input and output file names
input_file="data/repo-names-new.txt"

# List of issue template names
file_names=(".github/ISSUE_TEMPLATE.md" "issue_template.md" "ISSUE_TEMPLATE.md" ".github/issue_template.md" ".github/ISSUE_TEMPLATE" "ISSUE_TEMPLATE" "issue_template" ".github/issue_template")

# Check if the input file exists
if [ ! -f "$input_file" ]; then
  echo "Error: Input file '$input_file' not found."
  exit 1
fi

# Loop through the specified lines in the input file
for ((i=start; i<=end; i++)); do
  # Read the line from the input file and convert to lowercase
  line=$(sed -n "${i}p" "$input_file")
  line=$(echo "$line" | tr '[:upper:]' '[:lower:]')

  # Replace "/" with "--"
  output_file=$(echo "$line" | sed 's/\//--/g')
  repository="https://github.com/${line}.git"
  folder="${line#*/}"
  
  git clone "$repository"
  cd "$folder"
  if [ $? -ne 0 ]; then 
    echo "$line" >> "data/treatments/failed.txt"
    echo "Failed: $line"
    continue
  fi
  
  > "../data/treatments/${output_file}.txt"
  # Loop through the list
  for file in "${file_names[@]}"; do
    git log --all --format=%ad --date default -- "$file" | tail -1 \
      >> "../data/treatments/${output_file}.txt"
  done
  echo "Completed: $line"

  cd ..
  rm -rf "$folder"
done

echo "Lines $start to $end processed."
