import os
import re
import subprocess
import signal


def signal_handler(signum, frame):
    raise TimeoutError("Time out")


def set_timeout(seconds):
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)


def reset_timeout():
    signal.alarm(0)


def run_JUnit(bug_id, test_config, base_dir):
    buggy_dir = os.path.join(base_dir, bug_id + '_buggy')
    try:
        set_timeout(test_config['time_out'])
        cmd = 'defects4j test'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=buggy_dir)
        output, _ = process.communicate()
        output = output.decode('utf-8')
        reset_timeout()

        if 'Running ant (compile.tests)................................................ FAIL' in output:
            return False, 'Compile failed'
        else:
            match = re.search(r'Failing tests:\s*\d+', output)
            failing_test_result = match.group(0) if match else 'Failing tests count not found'
            return True if failing_test_result == 'Failing tests: 0' else False, failing_test_result
    except (RuntimeError, TimeoutError, Exception) as e:
        process.kill()
        return False, str(e)


def class_read(java_file_path):
    try:
        with open(java_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(java_file_path, 'r', encoding='iso-8859-1') as file:
            return file.read()


def class_write(java_file_path, content):
    if not os.access(java_file_path, os.W_OK):
        raise PermissionError(f"File is not writable: {java_file_path}")

    try:
        with open(java_file_path, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
    except PermissionError as e:
        raise RuntimeError(f"Permission denied: {java_file_path}") from e
    except OSError as e:
        raise RuntimeError(f"Write failed: {java_file_path}") from e


def extract_method_start_end_index(content, original_method):
    original_lines_tag = [line.strip() for line in original_method.splitlines() if line.strip()]  # Ignore empty lines in the original method, used for matching only
    # Split by line, keeping all lines (including blank lines)
    content_lines = content.splitlines()
    original_lines = original_method.splitlines()

    match_start = None
    for i in range(len(content_lines) - len(original_lines) + 1):
        # Get non-empty lines in the current window (for matching)
        window = [line.strip() for line in content_lines[i:i + len(original_lines)] if line.strip()]
        if window == original_lines_tag:
            match_start = i
            break

    if match_start is not None:
        # Calculate end line number, considering the number of non-empty lines in the original method
        match_end = match_start + len(original_lines)
        return [match_start, match_end]

    return None


def replace_file(java_file_path, method_replacements):
    content = class_read(java_file_path)
    class_lines = content.splitlines()  # Keep all lines, including blank lines

    for original_method, fixed_method in method_replacements:
        replace_index = extract_method_start_end_index(content, original_method)
        if replace_index is None:
            raise ValueError(f"Locate failed: Could not find method in {java_file_path}")

        fixed_method_lines = fixed_method.split('\n')

        class_lines[replace_index[0]:replace_index[1]] = fixed_method_lines

        # Update content and class_lines
        content = '\n'.join(class_lines)
        class_lines = content.splitlines()

    class_write(java_file_path, content)


def restore_file(bug_id, base_dir):
    buggy_dir = os.path.join(base_dir, f"{bug_id}_buggy")
    if not os.path.isdir(buggy_dir):
        return False

    try:
        # Force restore the entire repository
        result_reset = subprocess.run(["git", "reset", "--hard"], cwd=buggy_dir, capture_output=True, text=True)
        if result_reset.returncode != 0:
            print("Reset failed:", result_reset.stderr)
            return False

        # Clean untracked files and directories
        result_clean = subprocess.run(["git", "clean", "-fd"], cwd=buggy_dir, capture_output=True, text=True)
        if result_clean.returncode != 0:
            print("Clean failed:", result_clean.stderr)
            return False

        return True

    except Exception as e:
        print(f"Exception during restore: {e}")
        return False


def test(bug_id, file_replacements, base_dir):
    # Validate input
    if not file_replacements:
        return False, "No file replacements provided"

    test_config = {"time_out": 1200}

    restore_file(bug_id, base_dir=base_dir)

    try:
        # Replace methods in all files at once
        for java_file_path, method_replacements in file_replacements.items():
            print("java_file_path:", java_file_path)
            if not os.path.exists(java_file_path):
                raise ValueError(f"File not found: {java_file_path}")
            replace_file(java_file_path, method_replacements)
    except Exception as e:
        return False, f"Replace failed: {str(e)}"

    try:
        # Run JUnit test once
        reward, submission_result = run_JUnit(bug_id, test_config, base_dir)
        return reward, submission_result
    except Exception as e:
        return False, f"JUnit test failed: {str(e)}"