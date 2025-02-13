#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil  # New import for moving files

def parse_time_string(time_str):
    """
    Parse a time string in one of two formats:
      1) mm:ss.dd  (minutes:seconds[.fraction])
      2) ss.dd     (just seconds[.fraction])
    Returns a float (seconds) or None on failure.
    """
    time_str = time_str.strip()
    if not time_str:
        return None
    if ':' not in time_str:
        try:
            return float(time_str)
        except ValueError:
            return None
    else:
        # mm:ss or mm:ss.dd
        parts = time_str.split(':')
        if len(parts) != 2:
            return None
        try:
            minutes = int(parts[0])
            sec_frac = float(parts[1])
            return minutes * 60 + sec_frac
        except ValueError:
            return None

def has_audio_stream(input_file):
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=index',
        '-of', 'csv=p=0', input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return (result.returncode == 0 and result.stdout.strip() != '')

def get_video_duration(input_file):
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None

def remove_segments(input_file, segments):
    """
    segments: list of (start, end) tuples in seconds.
              A value of None means the beginning or end of the file.
    """
    duration = get_video_duration(input_file)
    if duration is None:
        print(f"Error: Cannot determine duration of {input_file}")
        return

    # Normalize segments: replace None with the appropriate 0 or duration.
    normalized = []
    for (start, end) in segments:
        s = 0.0 if start is None else start
        e = duration if end is None else end
        if e > s:
            normalized.append((s, e))

    # Sort and merge overlapping removal segments.
    normalized.sort(key=lambda x: x[0])
    merged = []
    for seg in normalized:
        if not merged:
            merged.append(seg)
        else:
            ps, pe = merged[-1]
            cs, ce = seg
            if cs <= pe:  # overlapping segments
                merged[-1] = (ps, max(pe, ce))
            else:
                merged.append(seg)

    # Build the list of segments to keep.
    keep = []
    current = 0.0
    for (rs, re) in merged:
        if rs > current:
            keep.append((current, rs))
        current = max(current, re)
    if current < duration:
        keep.append((current, duration))

    if not keep:
        print("All segments removed. Nothing left.")
        return

    audio_exists = has_audio_stream(input_file)

    # Build filter_complex instructions.
    lines = []
    vlabels = []
    alabels = []
    for i, (ks, ke) in enumerate(keep):
        vlabel = f"v{i}"
        lines.append(f"[0:v]trim={ks}:{ke},setpts=PTS-STARTPTS[{vlabel}]")
        vlabels.append(f"[{vlabel}]")
        if audio_exists:
            alabel = f"a{i}"
            lines.append(f"[0:a]atrim={ks}:{ke},asetpts=PTS-STARTPTS[{alabel}]")
            alabels.append(f"[{alabel}]")

    num_segments = len(keep)
    if audio_exists:
        pairs = []
        for v_label, a_label in zip(vlabels, alabels):
            pairs.append(v_label)
            pairs.append(a_label)
        pairs_str = ''.join(pairs)
        lines.append(f"{pairs_str}concat=n={num_segments}:v=1:a=1[outv][outa]")
    else:
        lines.append(f"{''.join(vlabels)}concat=n={num_segments}:v=1:a=0[outv]")

    filter_complex = ";".join(lines)
    base, ext = os.path.splitext(input_file)
    out = f"{base}_cut{ext}"

    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-filter_complex", filter_complex,
        "-map", "[outv]"
    ]
    if audio_exists:
        cmd += ["-map", "[outa]", "-c:a", "aac"]
    else:
        cmd += ["-an"]
    cmd += ["-c:v", "libx264", "-y", out]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

def archive_file(file_path):
    """
    Move the file to an "archive" subfolder within its directory.
    """
    abs_path = os.path.abspath(file_path)
    dir_name = os.path.dirname(abs_path)
    archive_dir = os.path.join(dir_name, "archive")
    if not os.path.exists(archive_dir):
        try:
            os.makedirs(archive_dir)
            print(f"Created archive folder: {archive_dir}")
        except Exception as e:
            print(f"Error creating archive folder {archive_dir}: {e}")
            return
    dest = os.path.join(archive_dir, os.path.basename(file_path))
    try:
        shutil.move(file_path, dest)
        print(f"Moved '{file_path}' to '{dest}'")
    except Exception as e:
        print(f"Error moving file {file_path} to archive: {e}")

def main():
    """
    Usage:
      ./remove_segments.py "start1,end1" "start2,end2" input1.mp4 input2.mp4 ...

    Each quoted argument with two values separated by a comma is treated as a removal segment.
    Leaving either the start or end empty indicates the beginning or end of the file.
    
    Examples:
      " ,2.34"  removes from the beginning until 2.34 seconds.
      "9.22, "  removes from 9.22 seconds to the end.
      "1.65,2.34" removes from 1.65 to 2.34 seconds.
      
    If only one value is provided without a comma, it is assumed to be the end time (i.e. remove from the beginning).
    """
    args = sys.argv[1:]
    if not args:
        print("Usage: remove_segments.py <segment1> [<segment2> ...] <file1> [<file2>...]")
        sys.exit(1)

    segments = []
    i = 0
    
    # Parse segment arguments (all arguments that are not existing files)
    while i < len(args):
        if os.path.isfile(args[i]):
            break
        seg_str = args[i]
        # Use a comma to split into two fields; this preserves empty fields.
        if ',' in seg_str:
            parts = seg_str.split(',', 1)
        else:
            # No comma: assume a single value (the end time) with removal from the beginning.
            parts = ['', seg_str]
        if len(parts) == 0:
            segments.append((None, None))
        elif len(parts) == 1:
            one = parse_time_string(parts[0])
            segments.append((None, one))
        else:
            s = parse_time_string(parts[0])
            e = parse_time_string(parts[1])
            segments.append((s, e))
        i += 1

    # The remaining arguments are treated as input files.
    input_files = args[i:]
    if not input_files:
        print("Error: No input files specified.")
        sys.exit(1)

    for f in input_files:
        if not os.path.isfile(f):
            print(f"Error: file '{f}' does not exist. Skipped.")
            continue
        remove_segments(f, segments)
        # After processing, move the original file to the "archive" subfolder.
        archive_file(f)

if __name__ == "__main__":
    main()
