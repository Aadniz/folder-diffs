# Folder diffs

Python script to compare folder structures, finding similar or duplicate folder structures. No hashsums involved, it only looks at the names. The script has some arguments to better narrow down the folder structures.

## Requirements

Check `requirements.txt`

- wcwidth

## Usage

It is only 1 file, the `main.py`.

### Basic Usage

```shell
python main.py /path/to/analyze
```

### Advanced Options

```shell
python main.py /path/to/analyze /another/path/to/analyze /yet/another/path \
  --max-size 10MB \
  --min-size 1KB \
  --min-files 2 \
  --max-depth 2 \
  --min-similarity 70 \
  -o /output/path/results.csv \
  --verbose
```

### Arguments

| Argument              | Description                                                                    |
|:----------------------|:-------------------------------------------------------------------------------|
| `paths`               | Paths to analyze (required)                                                    |
| `--max-size`          | Maximum folder size (e.g., `10MB`)                                             |
| `--min-size`          | Minimum folder size (e.g., `1KB`)                                              |
| `--min-files`         | Minimum number of files/folders in a folder (default: `1`)                     |
| `--max-depth`         | Maximum depth of subfolders to compare to each other (default: `1`)            |
| `--min-similarity`    | Minimum similarity percentage (0-100) to include in results (default: `50`)    |
| `-o`, `--output`      | Output file path for saving results (default: `/tmp/folder_diffs-{date}.csv)`  |
| `-i`, `--interactive` | Start interactive menu to merge, delete or skip folder matches                 |
| `--print`             | Force printing results to the console, even if there are more than 200 results |
| `-v`, `--verbose`     | Show verbose information                                                       |
| `--silent`            | Don't print anything during scanning                                           |
| `--sort`              | Sorting the result, can be size, similarity or name                            |

## Examples

### Example 1: Analyze a Directory

Analyzes all folders in `/home/user/Documents`, with default minimum similarity of `50%`.
Without any filters, this scan might take a long time to complate.

```shell
python main.py /home/user/Documents
```


### Example 2: Filter by Size and File Count

Analyzes all folders in `/home/user/Downloads`, skipping folders that are smaller than 100MB, that includes more than 4 files/folders.

```shell
python main.py /home/user/Downloads \
  --min-size 100MB \
  --min-files 5
```

### Example 3: Compare 2 directories with greater depth

Analyzes all folders in `/home/user/Downloads` and `/mnt/ssd/Downloads`, with a maximum depth of 2.
Spesifying the depth will give a more accurate representation of the folder match considering the subdirectories. It might however also end up not giving any results if set too high.

```shell
python main.py /home/user/Downloads /mnt/ssd/Downloads \
  --max-depth 2 \
```

### Example 4: Save Results to a CSV File

Analyzes all folders in `/home/user/Documents`, with minimum similarity of `80%` and outputs the results to a CSV file at `/home/user/results.csv`

```shell
python main.py /home/user/Documents \
  --min-similarity 80 \
  -o /home/user/results.csv
```

## Output
Output can be printed to standard output, or saved to a csv file.
Unless specified otherwise, it will save to a CSV file if there is more than 200 results.

### Console Output
```
10 directories to be compared
Similarity: 80.00%, Total Size: 2.44 KB
  Folder 1: /home/user/documents/folder1
  Folder 2: /home/user/documents/folder2

Similarity: 60.00%, Total Size: 2.93 KB
  Folder 1: /home/user/documents/folder1
  Folder 2: /home/user/documents/folder3

```

### CSV Output
```csv
Similarity,Total Size,Folder 1,Folder 2
0.8,2440,/home/user/documents/folder1,/home/user/documents/folder2
0.6,2935,/home/user/documents/folder1,/home/user/documents/folder3
```

### Interactive menu

Using the `-i` argument, you can enter interactive menu to delete, merge or skip folder matches.
For safety reasons, no *actual* deletions will happen. Rather, the paths to be deleted are appended to a file located in `/tmp`.

```
===                  ===
Entered interactive menu
===                  ===


What to do with:    (Structure similarity: 100.00%)
                 /tmp/test_folder/Documents 16.06 MB
/tmp/test_folder/backup/Downloads/Documents 16.06 MB
Merge up (mu), Merge down (md), Skip (s), Delete up (du), Delete down (dd), quit (q)
> du
========================
For safety reasons, are all deletions not done here. The paths are appended to /tmp/nix-shell.GbKSQQ/folder_diffs_deletion_paths_20250313.txt
Use an external program to delete these paths outside of the script
========================
Appended deletion: /tmp/test_folder/Documents >> /tmp/nix-shell.GbKSQQ/folder_diffs_deletion_paths_20250313.txt

What to do with:    (Structure similarity: 80.00%)
/tmp/test_folder/backup/Downloads 46.43 MB
       /tmp/test_folder/Downloads 15.19 MB
Merge up (mu), Merge down (md), Skip (s), Delete up (du), Delete down (dd), quit (q)
> dd
Appended deletion: /tmp/test_folder/Downloads >> /tmp/nix-shell.GbKSQQ/folder_diffs_deletion_paths_20250313.txt

What to do with:    (Structure similarity: 70.00%)
                    /tmp/test_folder/backup 47.30 MB
/tmp/test_folder/backup/Downloads/Documents 16.06 MB
Merge up (mu), Merge down (md), Skip (s), Delete up (du), Delete down (dd), quit (q)
> dd
Appended deletion: /tmp/test_folder/backup/Downloads/Documents >> /tmp/nix-shell.GbKSQQ/folder_diffs_deletion_paths_20250313.txt

What to do with:    (Structure similarity: 80.00%)
          /tmp/test_folder/backup/Downloads 46.43 MB
/tmp/test_folder/backup/Downloads/Downloads 15.19 MB
Merge up (mu), Merge down (md), Skip (s), Delete up (du), Delete down (dd), quit (q)
> du
Appended deletion: /tmp/test_folder/backup/Downloads >> /tmp/nix-shell.GbKSQQ/folder_diffs_deletion_paths_20250313.txt
```
