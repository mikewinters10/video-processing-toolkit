#!/usr/bin/env python3

import sys
import os
from PIL import Image
import shutil

def grid_cutter(image_path, M, N):
    # Open the image
    img = Image.open(image_path)
    img_width, img_height = img.size

    # Get the input image format (like 'JPEG', 'PNG', 'WEBP', etc.)
    image_format = img.format  # This keeps the original format

    # Calculate the width and height of each section
    section_width = img_width // N
    section_height = img_height // M

    # Get the directory, filename, and extension of the input image
    input_dir = os.path.dirname(image_path)
    input_filename, input_extension = os.path.splitext(os.path.basename(image_path))

    # Remove the leading dot from the extension and make it lower case (e.g. '.JPG' -> 'jpg')
    input_extension = input_extension[1:].lower()

    # Create the subdirectory for the specified grid size (e.g., "2x5")
    grid_folder_name = f"{M}x{N}"
    grid_folder_path = os.path.join(input_dir, grid_folder_name)
    os.makedirs(grid_folder_path, exist_ok=True)

    # Move the original image to the new folder after all cuts are done
    original_copy_path = os.path.join(grid_folder_path, os.path.basename(image_path))

    # Loop through the grid and save each section
    for i in range(M):
        for j in range(N):
            left = j * section_width
            upper = i * section_height
            right = (j + 1) * section_width
            lower = (i + 1) * section_height

            # Crop the image
            section = img.crop((left, upper, right, lower))

            # Generate the output filename for each section
            section_filename = f'{input_filename}_{i}_{j}.{input_extension}'

            # Save each section in the grid folder in the original format
            section.save(os.path.join(grid_folder_path, section_filename), image_format)

    # Now move the original image to the new folder
    shutil.move(image_path, original_copy_path)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python grid_cutter.py MxN <image_path1> <image_path2> ...")
        sys.exit(1)

    grid_size = sys.argv[1]
    image_paths = sys.argv[2:]  # Collect all the image paths after the grid size

    try:
        M, N = map(int, grid_size.split('x'))
    except ValueError:
        print("Grid size must be in the format MxN, where M and N are integers.")
        sys.exit(1)

    # Process each image provided in the arguments
    for image_path in image_paths:
        if not os.path.isfile(image_path):
            print(f"Error: Image file '{image_path}' not found.")
        else:
            print(f"Processing {image_path} with grid size {M}x{N}...")
            grid_cutter(image_path, M, N)
