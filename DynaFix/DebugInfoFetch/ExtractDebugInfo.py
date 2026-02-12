import json
import re
import shutil
import traceback
import os
import eventlet
import argparse
from filelock import FileLock
import concurrent.futures
from .Project import Project


def parse_id_range(id_range_str):
    """
    Parse ID range strings like '1-5,7-40,42' or '1,3-4', returning a list of integers.
    """
    ids = set()
    for part in id_range_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            ids.update(range(start, end + 1))
        else:
            ids.add(int(part))
    return sorted(ids)


def extract_debug_info(pid, bid, dynamic=False, width=0, iteration=0, args=None):
    """Extract debug info for the specified project and process method calls"""
    version_str = f"{pid}_{bid}b"
    buggy_str = f"{pid}_{bid}_buggy"

    # Select output path based on dynamic parameter
    if dynamic:
        if args is None:
            raise ValueError("args must be provided when dynamic=True")
        _debug_info_output = os.path.join(args.dynamic_output_path, "DebugInfo",
                                          f"{pid}_{bid}_width{width}_iter{iteration}.txt")
        _method_calls_output = os.path.join(args.dynamic_output_path, "MethodCalls",
                                            f"{pid}_{bid}_width{width}_iter{iteration}_method_calls.json")
        # Ensure output directory exists
        os.makedirs(os.path.join(args.dynamic_output_path, "DebugInfo"), exist_ok=True)
        os.makedirs(os.path.join(args.dynamic_output_path, "MethodCalls"), exist_ok=True)
    else:
        _debug_info_output = os.path.join(args.dynamic_output_path, "DebugInfo",
                                          f"{pid}_{bid}_width{width}_iter{iteration}.txt")
        _method_calls_output = os.path.join(args.dynamic_output_path, "MethodCalls",
                                            f"{pid}_{bid}_width{width}_iter{iteration}_method_calls.json")
        os.makedirs(os.path.join(args.dynamic_output_path, "DebugInfo"), exist_ok=True)
        os.makedirs(os.path.join(args.dynamic_output_path, "MethodCalls"), exist_ok=True)

    # Delete output file if it exists
    if os.path.exists(_debug_info_output):
        os.remove(_debug_info_output)
        print(f"Removed existing debug info: {_debug_info_output}")

    if os.path.exists(_method_calls_output):
        os.remove(_method_calls_output)
        print(f"Removed existing method calls info: {_method_calls_output}")

    # Use existing checkout path
    checkout_path = os.path.join(args.checkout_path, buggy_str)
    if not os.path.exists(checkout_path):
        print(f"Project {checkout_path} not found. Skipping...")
        return

    print(f"Using existing checkout at: {checkout_path}")

    try:
        project = Project(checkout_path)
    except Exception as e:
        print(f"Create project failed for {version_str}: {str(e)}")
        traceback.print_exc()
        return

    _locate_file = os.path.join(args.input_path, f"{pid}_{bid}b.txt")
    if not os.path.exists(_locate_file):
        print(f"Method location file not found for {pid}_{bid}b: {_locate_file}")
        return

    try:
        with open(_locate_file, "r") as _f:
            _methods_located = ",".join(_f.read().strip().splitlines())
    except Exception as e:
        print(f"Failed to read method location file for {pid}_{bid}b: {str(e)}")
        traceback.print_exc()
        return

    print(f"Running tests for {version_str}")
    try:
        trigger_test_methods = project.trigger_test_methods().split(",")
    except Exception as e:
        print(f"Failed to fetch trigger test methods for {version_str}: {str(e)}")
        traceback.print_exc()
        return

    d4j_root = os.path.dirname(args.major_root)
    d4j_executable = os.path.join(d4j_root, "framework", "bin", "defects4j")

    for method in trigger_test_methods:
        try:
            print(f"Running test method: {method}")
            with eventlet.Timeout(900):
                project.run_test(
                    single_test=method,
                    pid=pid,
                    bid=bid,
                    test_method=method,
                    methods_located=_methods_located,
                    d4j_exec=d4j_executable,
                    checkout_path=args.checkout_path
                )
        except eventlet.Timeout:
            print(f"Test execution timed out for {method} in {version_str}")
            continue
        except Exception as e:
            print(f"Failed to run test method {method} for {version_str}: {str(e)}")
            traceback.print_exc()
            continue

        # Extract debug info immediately after each test and append to file
        try:
            _debug_info = project.raw_debug_info()
            with open(_debug_info_output, "a") as f:
                f.write(f"\n=== Debug Info for Test: {method} ===\n")
                f.write(_debug_info)
        except Exception as e:
            print(f"Failed to extract or write debug info for {method} in {version_str}: {str(e)}")
            traceback.print_exc()
            continue

    # Extract method call information
    if os.path.exists(_debug_info_output):
        extract_method_calls_with_source(_debug_info_output, _method_calls_output, checkout_path)
    else:
        print(f"Debug info file not found for {version_str}: {_debug_info_output}")


def extract_method_with_doc_and_code(source_file, method_name):
    """Extract comment block and method code for specified Java method, returned separately, excluding internal method comments"""
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        method_pattern = re.compile(
            r'^\s*(?:public|protected|private|static|final|synchronized|abstract|\s)*' +
            r'(?:[\w\<\>\[\]]+\s+)+' + re.escape(method_name) + r'\s*\('
        )

        doc_block = []
        brace_count = 0
        in_doc = False
        in_method = False
        full_method_code = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("/**"):
                doc_block = [line.rstrip()]
                in_doc = True
                continue
            if in_doc:
                doc_block.append(line.rstrip())
                if "*/" in stripped:
                    in_doc = False
                continue
            if not in_method and method_pattern.search(line):
                in_method = True
                full_method_code = [line.rstrip()]
                brace_count += line.count("{") - line.count("}")
                continue
            if in_method:
                full_method_code.append(line.rstrip())
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0:
                    break

        if in_method:
            method_without_internal_comments = [
                l for l in full_method_code if not l.strip().startswith("//") and "/*" not in l and "*/" not in l
            ]
            return "\n".join(doc_block).strip(), "\n".join(method_without_internal_comments).strip()

        return None, None
    except Exception as e:
        return None, None


def extract_method_calls_with_source(debug_info_file, output_file, checkout_path):
    """Extract called methods, and extract corresponding method definitions (comments and code separated, output as JSON)"""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        method_calls = set()

        with open(debug_info_file, "r") as f:
            for line in f:
                line = line.strip()
                if "[Method Call]" in line and "->" in line:
                    try:
                        call_part = line.split("->", 2)[2].strip()
                        method_calls.add(call_part)
                    except Exception:
                        continue

        output_data = []
        for full_method in sorted(method_calls):
            if full_method.startswith(("java.", "javax.")):
                continue

            try:
                class_parts = full_method.split(".")
                method_name = class_parts[-1]
                class_path = ".".join(class_parts[:-1]).replace(".", "/") + ".java"

                if method_name == "<init>":
                    continue

                # Possible source directories
                src_dirs = ["source", "src/main/java", "src/java", "src"]
                source_file = None
                for src_dir in src_dirs:
                    for root, _, files in os.walk(os.path.join(checkout_path, src_dir)):
                        for file in files:
                            if file.endswith(".java") and class_path in os.path.join(root, file):
                                source_file = os.path.join(root, file)
                                break
                        if source_file:
                            break

                if not source_file or not os.path.exists(source_file):
                    output_data.append({
                        "method": full_method,
                        "doc": "[Source file not found]",
                        "code": ""
                    })
                    continue

                doc, code = extract_method_with_doc_and_code(source_file, method_name)
                output_data.append({
                    "method": full_method,
                    "doc": doc if doc else "[No documentation]",
                    "code": code if code else "[No method body]"
                })
            except Exception as e:
                output_data.append({
                    "method": full_method,
                    "doc": "[Extraction failed]",
                    "code": str(e)
                })

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Method source information (JSON) written to: {output_file}")
    except Exception as e:
        print(f"Failed to process {debug_info_file}: {str(e)}")
        traceback.print_exc()


def replace_ant_and_extract_debug_info(pid, bid, width, j, args):
    """
    Replace ant and extract debug info (lock-free version)
    Prerequisite: When calling this function, the directory pointed to by args.major_root is exclusive to the current process and not shared with other processes.
    """
    ant_dir = os.path.join(args.major_root, "bin")
    ant_original = os.path.join(ant_dir, "ant")
    _debug_ant_path = os.path.join(ant_dir, "ant_debug")
    ant_backup = os.path.join(ant_dir, "ant.tmp_backup")

    if not os.path.exists(_debug_ant_path):
        raise Exception(f"[ERROR] debug_ant path {_debug_ant_path} does not exist. Please check.")

    # 1. Backup original ant
    if os.path.exists(ant_original):
        try:
            shutil.copy2(ant_original, ant_backup)
        except Exception as e:
            raise Exception(f"[ERROR] Failed to backup ant: {str(e)}")
    else:
        raise Exception(f"[ERROR] Original ant file {ant_original} does not exist")

    # 2. Replace with debug_ant
    try:
        shutil.copy2(_debug_ant_path, ant_original)
    except Exception as e:
        print(f"[ERROR] Failed to replace debug_ant: {str(e)}")
        # If replacement fails, try to restore the backup file to keep the environment unchanged
        if os.path.exists(ant_backup):
            shutil.move(ant_backup, ant_original)
        raise

    # 3. Execute task and ensure restoration
    try:
        # Extract debug info
        extract_debug_info(pid, bid, dynamic=True, width=width, iteration=j, args=args)
    finally:
        # 4. Restore original ant (will execute regardless of errors above)
        if os.path.exists(ant_backup):
            try:
                # Move backup file back to original location
                shutil.move(ant_backup, ant_original)
                print(f"[INFO] Restored original ant: {ant_original}")
            except Exception as e:
                print(f"[WARNING] Failed to restore original ant: {str(e)}")
        else:
            print(f"[WARNING] No backup found for ant: {ant_backup}, nothing restored.")