#!/usr/bin/env python3

import os
import sys
import csv
import tempfile
import argparse
import wcwidth
from datetime import datetime
from typing import List, Tuple, Dict, Set

def parse_size(size_str: str) -> int:
    """
    Convert size string with units (B, KB, MB, GB) to bytes.
    """
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    size_str = size_str.upper()
    if size_str[-2:] in units:
        num, unit = size_str[:-2], size_str[-2:]
    elif size_str[-1] in units:
        num, unit = size_str[:-1], size_str[-1]
    else:
        num, unit = size_str, "B"
    return int(float(num) * units[unit])

def human_readable_size(size_bytes: int) -> str:
    """
    Convert a size in bytes to a human-readable format (e.g., KB, MB, GB).
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1

    return f"{size_bytes:.2f} {units[unit_index]}"

def get_folder_size(path: str) -> int:
    """
    Calculate the total size of the folder in bytes.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.islink(fp):
                continue
            total_size += os.path.getsize(fp)
    return total_size

def get_folder_contents(path: str, max_depth: int = 1, current_depth: int = 0) -> Set[str]:
    """
    Get the list of files and folders in the given directory, skipping symbolic links.
    If max_depth > 1, recursively traverse subdirectories up to the specified depth.
    """
    contents = set()
    try:
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            if os.path.islink(full_path):  # Skip symbolic links
                continue
            contents.add(name)
            if os.path.isdir(full_path) and current_depth < max_depth - 1:
                # Recursively get contents of subdirectories
                sub_contents = get_folder_contents(full_path, max_depth, current_depth + 1)
                contents.update(f"{name}/{item}" for item in sub_contents)
    except PermissionError as e:
        print(e)
    return contents

def compare_folders(folder1: str, folder2: str, max_depth: int = 1) -> float:
    """
    Compare two folders and return a similarity score.
    """
    contents1 = get_folder_contents(folder1, max_depth)
    contents2 = get_folder_contents(folder2, max_depth)
    common = contents1.intersection(contents2)
    total = max(len(contents1), len(contents2))
    if total == 0:
        return 0.0
    return len(common) / total

def print_handler(text: str, verbose: bool = False, silent: bool = False):
    """
    Print handler, either printing on one line or the normal way depending on verbose settings
    """
    if silent:
        return
    if verbose:
        print(text)
    else:
        terminal_width = os.get_terminal_size()[0]
        if len(text) != wcwidth.wcswidth(text):  # Wide characters like Japanese characters
            truncated_text = ""
            current_width = 0
            for char in text:
                char_width = wcwidth.wcwidth(char)
                if current_width + char_width > terminal_width:
                    break
                truncated_text += char
                current_width += char_width
            print(truncated_text, end="\r")
        else:
            print(text[:terminal_width], end="\r")
        sys.stdout.write('\x1b[2K')

def save_to_csv(results: List[Dict[str, str]], output_file: str):
    """Save the results to a CSV file."""
    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Similarity", "Total Size","Folder 1", "Folder 2"])
        for entry in results:
            writer.writerow([
                entry['similarity'],
                entry["size"],
                os.path.abspath(entry["folder1"]),
                os.path.abspath(entry["folder2"])
            ])

def main():
    parser = argparse.ArgumentParser(description="Find duplicate or similar folder structures.")
    parser.add_argument("PATHS", type=str, nargs="+", help="Paths to analyze")
    parser.add_argument("--max-size", type=str, help="Maximum folder size (e.g., 10MB)")
    parser.add_argument("--min-size", type=str, help="Minimum folder size (e.g., 1KB)")
    parser.add_argument("-f", "--min-files", type=int, default=1, help="Minimum number of files/folders in folders")
    parser.add_argument("-s", "--min-similarity", type=float, default=50.0, help="Minimum similarity percentage (0-100)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output file path for saving results (default: system temp directory)")
    parser.add_argument("-p", "--print", action="store_true", help="Print results to console")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose information (will slow down the scan)")
    parser.add_argument("--silent", action="store_true", help="Don't print anything during scanning (will speed up scan)")
    parser.add_argument("--max-depth", type=int, default=1, help="Set the max depth to compare folder similarities to")
    parser.add_argument("--sort", type=str, choices=["name", "similarity", "size"], default="similarity", help="Sort results by name, similarity, or size (default: similarity)")

    args = parser.parse_args()

    # Check if any path is a subdirectory of another
    has_overlaps = False
    for i in range(len(args.PATHS)):
        for j in range(i + 1, len(args.PATHS)):
            if is_subdirectory(args.PATHS[i], args.PATHS[j]) or is_subdirectory(args.PATHS[j], args.PATHS[i]):
                print(f"Error: Paths cannot overlap: {args.PATHS[i]} and {args.PATHS[j]}")
                has_overlaps = True
    if has_overlaps:
        sys.exit(1)

    # Determine the output file path
    temp_dir = tempfile.gettempdir()
    output_file = args.output if args.output is not None else os.path.join(temp_dir, f"folder_diffs_{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv")

    # Convert size arguments to bytes
    max_size = parse_size(args.max_size) if args.max_size else float('inf')
    min_size = parse_size(args.min_size) if args.min_size else 0

    print("Counting total directories to check...")
    total_dirs = 0
    for path in args.PATHS:
        for root, dirs, files in os.walk(path, followlinks=False):
            total_dirs += len(dirs)

    # Collect all folders that meet the size and file count criteria
    folders = []
    processed_dirs = 0
    for path in args.PATHS:
        for root, dirs, files in os.walk(path, followlinks=False):
            # Remove symbolic links from the list of directories to traverse
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                progress = (processed_dirs / total_dirs) * 100
                print_handler(f"Gathering folders... {progress:.2f}% {dir_path}", args.verbose, args.silent)
                dir_size = get_folder_size(dir_path)
                if min_size <= dir_size <= max_size and len(get_folder_contents(dir_path, args.max_depth)) >= args.min_files:
                    folders.append({
                        "path": dir_path,
                        "size": dir_size
                    })
                processed_dirs += 1

    # Collecting all similarities comparing all folders against all folders
    similarities = []
    total_comparisons = len(folders) * (len(folders) - 1) // 2
    completed_comparisons = 0
    if not args.silent:
        print(f"{total_comparisons} directories to be compared")
    # Calculate print interval to ensure no more than 1 million print operations
    print_interval = max(1, total_comparisons // 1_000_000)  # Print every N comparisons
    for i in range(len(folders)):
        for j in range(i + 1, len(folders)):
            progress = (completed_comparisons / total_comparisons) * 100
            if completed_comparisons % print_interval == 0:
                print_handler(f"Comparing... {progress:.2f}% {folders[i]['path']} <-> {folders[j]['path']}", args.verbose, args.silent)
            similarity = compare_folders(folders[i]["path"], folders[j]["path"], args.max_depth)
            if similarity * 100.0 >= args.min_similarity:
                similarities.append({
                    "folder1": folders[i]["path"],
                    "folder2": folders[j]["path"],
                    "similarity": similarity,
                    "size": folders[i]["size"] + folders[j]["size"]
                })
            completed_comparisons += 1

    if args.sort == "name":
        similarities.sort(key=lambda x: (x["folder1"], x["folder2"], -x["similarity"], -x["size"]))
    elif args.sort == "size":
        similarities.sort(key=lambda x: (-x["size"], -x["similarity"], x["folder1"], x["folder2"]))
    else:
        similarities.sort(key=lambda x: (-x["similarity"], -x["size"], x["folder1"], x["folder2"]))

    if len(similarities) < 200 or args.print:
        for entry in similarities:
            print(f"Similarity: {(entry['similarity'] * 100):.2f}%, Total Size: {human_readable_size(entry['size'])}")
            print(f"  Folder 1: {entry['folder1']}")
            print(f"  Folder 2: {entry['folder2']}")
            print()
    else:
        if not args.print:
            print("Too many results to print to stdout.")
            print("Use `-p` to force print it if wanted")

        save_to_csv(similarities, output_file)
        print(f"Results saved to: {output_file}")

if __name__ == '__main__':
    main()
