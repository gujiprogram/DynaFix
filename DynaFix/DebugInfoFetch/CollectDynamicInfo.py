import json
import re
import shutil
import threading
import traceback
import os
import eventlet
import argparse
from filelock import FileLock
import concurrent.futures
from Project import Project
from ExtractDebugInfo import *
import ast

parser = argparse.ArgumentParser(description="Extract debug information for Defects4J projects")
parser.add_argument('--output_path', default="/path/to/output", type=str,
                    help="Path to output debug info and method calls")
parser.add_argument('--input_path', default="/path/to/input", type=str,
                    help="Path to input method location files")
parser.add_argument('--checkout_path', default="/path/to/defects4j_buggy", type=str,
                    help="Path to checked-out Defects4J projects")
parser.add_argument('--major_root', default="/path/to/defects4j/major", type=str,
                    help="Path to Defects4J major root")
args = parser.parse_args()

eventlet.monkey_patch()

# ========== Replace ant with ant_debug ==========
_debug_ant_path = os.path.join(args.major_root, "bin", "ant_debug")
if not os.path.exists(_debug_ant_path):
    raise Exception(f"debug_ant path {_debug_ant_path} does not exist. Please set DEBUG_ANT.")

ant_original = os.path.join(args.major_root, "bin", "ant")
ant_backup = os.path.join(args.major_root, "bin", "ant_backup")

# Backup original ant
if os.path.exists(ant_original) and not os.path.exists(ant_backup):
    shutil.copy2(ant_original, ant_backup)
else:
    print(f"Original ant not found or already backed up: {ant_original}")

# Replace with debug_ant
shutil.copy2(_debug_ant_path, ant_original)

try:
    # ========== Main logic starts ==========

    # Regular expression matching filename format "{pid}_{bid}b_{num}.txt"
    file_pattern = re.compile(r"(\w+)_(\d+)b_(\d+)\.txt")

    # Get all filenames in the folder
    all_ids = []
    for filename in os.listdir(args.input_path):
        match = file_pattern.match(filename)
        if match:
            pid, bid, num = match.groups()
            all_ids.append((pid, int(bid), int(num)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(extract_debug_info, pid, bid, num, dynamic=False, iteration=0, args=args)
            for pid, bid, num in all_ids
        ]
        concurrent.futures.wait(futures)

finally:
    # ========== Restore original ant ==========
    if os.path.exists(ant_backup):
        os.remove(ant_original)
        shutil.copy2(ant_backup, ant_original)
        os.remove(ant_backup)
        print(f"Restored original ant: {ant_original}")
    else:
        print("No backup ant found; original ant may not have been modified.")