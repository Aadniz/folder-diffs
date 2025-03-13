#!/usr/bin/env python3

import os
import sys
import csv
import tempfile
import shutil
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
        writer.writerow(["Similarity", "Path 1", "Size 1", "Path 2", "Size 2"])
        for entry in results:
            writer.writerow([
                entry['similarity'],
                os.path.abspath(entry["folder1"]),
                entry["folder1_size"],
                os.path.abspath(entry["folder2"]),
                entry["folder2_size"]
            ])

def interactive_menu(similarities: List[Dict[str, str]]):
    print("===                  ===")
    print("Entered interactive menu")
    print("===                  ===")
    print()

    temp_dir = tempfile.gettempdir()
    deletion_paths_file = os.path.join(temp_dir, f"folder_diffs_deletion_paths_{datetime.now().strftime('%Y%m%d')}.txt")
    has_shown_warning = False
    deleted_paths = []

    def append_deletion_path(filename, content):
        deletion_warning_message()
        with open(filename, "a") as myfile:
            myfile.write(content + "\n")
        print(f"Appended deletion: {content} >> {filename}")

    def deletion_warning_message():
        nonlocal has_shown_warning, deletion_paths_file
        if has_shown_warning:
            return
        print("========================")
        print(f"For safety reasons, are all deletions not done here. The paths are appended to {deletion_paths_file}")
        print("Use an external program to delete these paths outside of the script")
        print("========================")
        has_shown_warning = True

    def remove_related_paths(similarities, deleted_path):
        """
        Remove entries from the similarities list that involve the deleted path.
        """
        new_similarities = []
        for entry in similarities:
            path1 = entry["folder1"]
            path2 = entry["folder2"]
            if path1.startswith(deleted_path) or path2.startswith(deleted_path):
                continue
            new_similarities.append(entry)
        return new_similarities


    def right_aligned(text, total_width):
        """
        Right-align text within a given width, handling Unicode characters correctly.
        """
        display_width = wcwidth.wcswidth(text)
        if display_width > total_width:
            cut_length = total_width - 3  # Reserve 3 spaces for '...'
            while wcwidth.wcswidth(text[:cut_length]) > total_width - 3:
                cut_length -= 1
            text = text[:cut_length] + '...'
        else:
            padding = total_width - display_width
            text = ' ' * padding + text
        return text

    for entry in list(similarities):
        # Set path1 and size1 to the biggest folder
        if entry["folder1_size"] >= entry["folder2_size"]:
            path1 = entry["folder1"]
            path2 = entry["folder2"]
            size1 = entry["folder1_size"]
            size2 = entry["folder2_size"]
        else:
            path1 = entry["folder2"]
            path2 = entry["folder1"]
            size1 = entry["folder2_size"]
            size2 = entry["folder1_size"]

        # Skip if already been marked as deleted
        skip = False
        for path in deleted_paths:
            if path1.startswith(path) or path2.startswith(path):
                skip = True
                break
        if skip:
            continue

        human_size1 = human_readable_size(size1)
        human_size2 = human_readable_size(size2)
        similarity = entry['similarity']

        # Some astetics
        terminal_width = os.get_terminal_size()[0]
        longest_path_len = min(max(wcwidth.wcswidth(path1), wcwidth.wcswidth(path2)), terminal_width - max(len(human_size1), len(human_size2)) - 1)

        print(f"\nWhat to do with:    (Structure similarity: {(similarity * 100):.2f}%)")
        print(right_aligned(path1, longest_path_len) + " " + human_size1)
        print(right_aligned(path2, longest_path_len) + " " + human_size2)
        print("Merge up (mu), Merge down (md), Skip (s), Delete up (du), Delete down (dd), quit (q)")
        while True:
            choice = input("> ").strip()
            if choice == "mu":
                print(f"Merging {path2} into {path1}...")
                shutil.copytree(path2, path1, dirs_exist_ok=True)
                print("Merge complete.")
                append_deletion_path(deletion_paths_file, path2)
                deleted_paths.append(path2)
                break
            elif choice == "md":
                print(f"Merging {path1} into {path2}...")
                shutil.copytree(path1, path2, dirs_exist_ok=True)
                print("Merge complete.")
                append_deletion_path(deletion_paths_file, path1)
                deleted_paths.append(path1)
                break
            elif choice == "s":
                print("Skipping...")
                break
            elif choice == "du":
                append_deletion_path(deletion_paths_file, path1)
                deleted_paths.append(path1)
                break
            elif choice == "dd":
                append_deletion_path(deletion_paths_file, path2)
                deleted_paths.append(path2)
                break
            elif choice == "q":
                print("Quitting...")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")

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
    parser.add_argument("-i", "--interactive", action="store_true", help="Enable interactive menu for merging folders")
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
                    "folder1_size": folders[i]["size"],
                    "folder2_size": folders[j]["size"],
                    "similarity": similarity
                })
            completed_comparisons += 1

    if args.sort == "name":
        similarities.sort(key=lambda x: (x["folder1"], x["folder2"], -x["similarity"], -(x["folder1_size"] + x["folder2_size"])))
    elif args.sort == "size":
        similarities.sort(key=lambda x: (-(x["folder1_size"] + x["folder2_size"]), -x["similarity"], x["folder1"], x["folder2"]))
    else:
        similarities.sort(key=lambda x: (-x["similarity"], -(x["folder1_size"] + x["folder2_size"]), x["folder1"], x["folder2"]))

    if len(similarities) < 200 or args.print:
        for entry in similarities:
            print(f"Similarity: {(entry['similarity'] * 100):.2f}%")
            print(f"  Dir 1: {human_readable_size(entry['folder1_size'])}\t{entry['folder1']}")
            print(f"  Dir 2: {human_readable_size(entry['folder2_size'])}\t{entry['folder2']}")
            print()
    else:
        if not args.print:
            print(f"Too many results ({len(similarities)}) to print to stdout.")
            print("Use `-p` to force print it if wanted")

        save_to_csv(similarities, output_file)
        print(f"Results saved to: {output_file}")

    if args.interactive:
        interactive_menu(similarities)

if __name__ == '__main__':
    main()
