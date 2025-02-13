#!/usr/bin/env python3

import os
import cv2
import sys
import math

def create_screenshots(video_path, output_dir, current_idx, total_files, approx_elements, no_grid=False):
    """
    Creates screenshots from the given video_path.
    If no_grid is True, saves each screenshot individually.
    Otherwise, concatenates them into a single grid image.
    """

    base_name = os.path.basename(video_path)
    name_no_ext = os.path.splitext(base_name)[0]

    # Decide on the name(s) for output
    if no_grid:
        # We'll create multiple files named like: <videoName>_screen_1.jpg, etc.
        # We won't check if they exist beforehand, but you could if you like
        screenshot_path = None
    else:
        # Single grid filename
        screenshot_name = f"{name_no_ext}-screen.jpg"
        screenshot_path = os.path.join(output_dir, screenshot_name)

        # If the grid is already present, skip
        if os.path.exists(screenshot_path):
            print(f"{current_idx}/{total_files} - Screenshot grid already exists for {screenshot_name}, skipping...")
            return

    # Open the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Failed to open video {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Determine orientation and best rows x cols distribution
    is_landscape = frame_width > frame_height
    max_rows = 3 if is_landscape else 2
    cols = math.ceil(math.sqrt(approx_elements))
    rows = math.ceil(approx_elements / cols)

    if rows > max_rows:
        rows = max_rows
        cols = math.ceil(approx_elements / rows)

    # We'll collect frames in memory (for the grid) or write them out individually
    grid = None

    screenshot_index = 0
    for i in range(rows):
        row = None
        for j in range(cols):
            # Calculate which frame index to grab
            # evenly spaced across the total_frames
            frame_idx = int((i * cols + j) * total_frames / (rows * cols))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                print(f"Failed to read frame at index {frame_idx} from {video_path}")
                continue

            screenshot_index += 1

            if no_grid:
                # Save this frame as a separate file
                # e.g. "videoName_screen_1.jpg", "videoName_screen_2.jpg", ...
                out_filename = f"{name_no_ext}_screen_{screenshot_index}.jpg"
                out_path = os.path.join(output_dir, out_filename)
                cv2.imwrite(out_path, frame)
            else:
                # For the grid, accumulate horizontally in row
                if row is None:
                    row = frame
                else:
                    try:
                        row = cv2.hconcat([row, frame])
                    except cv2.error as e:
                        print(f"Error concatenating frames horizontally: {e}")
                        cap.release()
                        return

        # Accumulate each finished row vertically to form the full grid
        if not no_grid and row is not None:
            if grid is None:
                grid = row
            else:
                try:
                    grid = cv2.vconcat([grid, row])
                except cv2.error as e:
                    print(f"Error concatenating rows vertically: {e}")
                    cap.release()
                    return

    cap.release()

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    if no_grid:
        # We have already saved each screenshot individually
        print(f"{current_idx}/{total_files} - Individual screenshots saved to '{output_dir}' for {base_name}")
    else:
        # Write out the single grid image
        if grid is not None:
            cv2.imwrite(screenshot_path, grid)
            print(f"{current_idx}/{total_files} - Screenshot grid saved as {screenshot_path}")
        else:
            print(f"{current_idx}/{total_files} - No valid frames were found to create a grid for {base_name}")

if __name__ == '__main__':
    # Collect arguments (excluding script name)
    args = sys.argv[1:]

    # Initialize flags
    no_grid = False
    use_input_dir = False

    # Check for --no-grid and --k flags
    if '--no-grid' in args:
        no_grid = True
        args.remove('--no-grid')

    if '--k' in args:
        use_input_dir = True
        args.remove('--k')

    # Now we expect at least 2 arguments: <approx_elements> <video1> [<video2> ...]
    if len(args) < 2:
        print("Usage: python grid_creator.py <approx_elements> [--no-grid] [--k] <video_files...>")
        print("Example (grid in 'screens' folder): python grid_creator.py 9 video1.mp4 video2.mov video3.gif")
        print("Example (no grid): python grid_creator.py 9 --no-grid video1.mp4 video2.mov")
        print("Example (grid in input file's directory): python grid_creator.py 9 --k video1.mp4 video2.mov")
        print("Example (no grid and grid in input file's directory): python grid_creator.py 9 --no-grid --k video1.mp4 video2.mov")
        sys.exit(1)

    # First arg is number of elements
    try:
        approx_elements = int(args[0])
    except ValueError:
        print("Error: Number of elements must be an integer.")
        sys.exit(1)

    # The rest are video files
    video_files = args[1:]
    total_files = len(video_files)

    for idx, video_file in enumerate(video_files, start=1):
        video_file = os.path.abspath(video_file)

        if not os.path.isfile(video_file):
            print(f"File not found: {video_file}")
            continue

        # Check file extension
        if not video_file.lower().endswith(('.mp4', '.mov', '.gif', '.MOV')):
            print(f"Unsupported file type: {video_file}")
            continue

        # Determine output directory based on --k flag
        video_dir = os.path.dirname(video_file)
        if use_input_dir:
            output_dir = video_dir
        else:
            output_dir = os.path.join(video_dir, "screens")

        create_screenshots(
            video_file,
            output_dir,
            current_idx=idx,
            total_files=total_files,
            approx_elements=approx_elements,
            no_grid=no_grid
        )
a