from PIL import Image
import sys
import os
import random

def flip_image_horizontally(input_image_path):
    try:
        # Open the input image
        img = Image.open(input_image_path)
        
        # Flip the image horizontally
        flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
        
        # Save the flipped image, overwriting the original file
        flipped_img.save(input_image_path)
        
        print(f"Flipped image saved, overwriting {input_image_path}")
    
    except Exception as e:
        print(f"Error processing '{input_image_path}': {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python flip_image.py <input_image_path1> <input_image_path2> ...")
    else:
        for input_image_path in sys.argv[1:]:
            if not os.path.exists(input_image_path):
                print(f"Error: Input file '{input_image_path}' does not exist.")
            else:
                # Randomly decide whether to flip the image (50% chance)
                if random.random() < 0.5:
                    flip_image_horizontally(input_image_path)
                else:
                    print(f"Skipped flipping '{input_image_path}'")

