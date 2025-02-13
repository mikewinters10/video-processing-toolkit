#!/usr/bin/env python3

import sys
import os
from PIL import Image, ImageOps
import numpy as np
from moviepy.editor import ImageSequenceClip, VideoFileClip

def convert_gif_to_mp4(input_file_path):
    if not os.path.isfile(input_file_path):
        print(f"Error: File '{input_file_path}' does not exist.")
        return False  # Indicate failure

    if not input_file_path.lower().endswith('.gif'):
        print(f"Error: '{input_file_path}' is not a GIF file.")
        return False  # Indicate failure

    try:
        # Read frames and durations from the GIF
        im = Image.open(input_file_path)

        frames = []
        durations = []

        try:
            while True:
                frame = im.copy().convert('RGB')
                duration_ms = im.info.get('duration', 100)
                if duration_ms == 0:
                    duration_ms = 100  # Default to 100 ms if duration is zero
                durations.append(duration_ms / 1000)  # Convert to seconds

                # Ensure dimensions are divisible by 2
                width, height = frame.size
                new_width = width + (width % 2)
                new_height = height + (height % 2)

                if (width != new_width) or (height != new_height):
                    # Pad the image to make dimensions even
                    frame = ImageOps.expand(
                        frame,
                        border=(0, 0, new_width - width, new_height - height),
                        fill=(0, 0, 0)
                    )

                frames.append(np.array(frame))

                im.seek(im.tell() + 1)
        except EOFError:
            pass  # End of sequence

        total_duration = sum(durations)

        # Create an ImageSequenceClip with the frames and durations
        clip = ImageSequenceClip(frames, durations=durations)

        # Define output file path
        input_dir = os.path.dirname(input_file_path)
        input_base_name = os.path.basename(input_file_path)
        output_base_name = os.path.splitext(input_base_name)[0] + '.mp4'
        output_file_path = os.path.join(input_dir, output_base_name)

        # Write the video file with fps=25
        clip.write_videofile(
            output_file_path,
            fps=25,  # Added fps parameter here
            codec='libx264',
            audio=False,
            threads=1,
            ffmpeg_params=[
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'baseline',
                '-level', '3.0'
            ],
            verbose=False,
            logger=None
        )

        # Close the clip
        clip.close()

        # Verify that the output video has the same duration
        output_clip = VideoFileClip(output_file_path)
        mp4_duration = output_clip.duration
        output_clip.close()

        # Compare durations
        duration_diff = abs(total_duration - mp4_duration)
        if duration_diff > 0.1:  # Allow a small difference of 100 ms
            print(f"Warning: The durations of '{input_base_name}' GIF and MP4 differ by {duration_diff:.3f} seconds.")
        else:
            print(f"Conversion successful for '{input_base_name}'. The durations match.")
        return True  # Indicate success

    except Exception as e:
        print(f"An error occurred while processing '{input_file_path}': {e}")
        return False  # Indicate failure

def main():
    # Parse arguments and check for '--save' flag
    args = sys.argv[1:]
    save_original = False
    if '--save' in args:
        save_original = True
        args.remove('--save')

    if not args:
        print("Usage: ./convert-gif-to-mp4.py [--save] <input_file1> <input_file2> ...")
        sys.exit(1)

    input_file_paths = args

    for input_file_path in input_file_paths:
        print(f"Processing '{input_file_path}'...")
        success = convert_gif_to_mp4(input_file_path)

        # If conversion succeeded and user did not request to save the original, delete the GIF
        if success and (not save_original):
            # Confirm the output MP4 exists before deleting
            output_file = os.path.splitext(input_file_path)[0] + '.mp4'
            if os.path.exists(output_file):
                try:
                    os.remove(input_file_path)
                    print(f"Deleted original GIF: '{input_file_path}'.")
                except Exception as e:
                    print(f"Could not delete '{input_file_path}': {e}")

        print("")  # Add an empty line for readability

if __name__ == "__main__":
    main()
