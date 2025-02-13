#!/usr/bin/env python3

import argparse
from PIL import Image, ImageSequence
import sys

def rotate_gif(input_path, rotation):
    # Open the input GIF
    gif = Image.open(input_path)
    
    # Rotate each frame
    frames = []
    for frame in ImageSequence.Iterator(gif):
        rotated_frame = frame.rotate(rotation, expand=True)
        frames.append(rotated_frame)
    
    # Save the rotated frames back to the original file
    frames[0].save(
        input_path,
        save_all=True,
        append_images=frames[1:],
        duration=gif.info['duration'],
        loop=gif.info.get('loop', 0),
        disposal=2
    )
    print(f"Rotated GIF saved and overwritten as {input_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate one or more GIFs counterclockwise by a specified degree.")
    parser.add_argument("--r", type=float, required=True, help="Degrees to rotate the GIF counterclockwise.")
    parser.add_argument("input", nargs="+", help="Paths to the input GIF files.")
    args = parser.parse_args()
    
    for input_path in args.input:
        try:
            rotate_gif(input_path, args.r)
        except Exception as e:
            print(f"Error rotating {input_path}: {e}", file=sys.stderr)
