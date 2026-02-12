import os
import subprocess
import traceback
from dotenv import dotenv_values, find_dotenv, load_dotenv

# Load environment variables
_ = load_dotenv(find_dotenv())

# Set ignore paths
ignore_paths = ["/.git", "/.classes.tmp", "/target", "/.idea"]

# Define log file names
DEBUG_LOG_NAME = "bugDetect.log"
ORI_DEBUG_LOG_NAME = "bugDetectOri.log"
D4J_FAILING_TEST = "failing_tests"

# Defects4J configuration keys
D4J_RELEVANT_KEY = "d4j.classes.relevant"
D4J_SRC_PATH_KEY = "d4j.dir.src.classes"
D4J_TEST_PATH_KEY = "d4j.dir.src.tests"
D4J_TRIGGER_KEY = "d4j.tests.trigger"

KEY_ARGS_USE_SPECIFIED = "args.use.specified"
KEY_ARGS_METHODS = "args.methods"


class Project:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        _d4j_file_name = os.path.join(base_dir, "defects4j.build.properties")
        if not os.path.exists(_d4j_file_name):
            raise FileNotFoundError("No defects4j.build.properties file found")
        self._d4j_configs = dotenv_values(_d4j_file_name)
        self._trigger_test_methods = self._d4j_configs.get(D4J_TRIGGER_KEY)
        if not self._trigger_test_methods:
            raise ValueError(f"Missing {D4J_TRIGGER_KEY} in defects4j.build.properties")
        # Added: store dynamic log paths
        self._bug_detect_log = None
        self._bug_detect_ori_log = None

    def trigger_test_methods(self):
        return self._trigger_test_methods

    def run_test(self, single_test: str = None, relevant=True, pid: str = None, bid: int = None,
                 test_method: str = None, methods_located: str = None,
                 d4j_exec: str = None, checkout_path: str = None):
        """
        Run test and generate dynamic trace logs.
        d4j_exec: Dynamically specified defects4j executable path
        checkout_path: Dynamically specified project checkout parent directory
        """
        # 1. Path decision: prioritize passed arguments, otherwise fallback to environment variables (compatible with old logic)
        _d4j_exec = d4j_exec if d4j_exec else D4J_EXEC
        _checkout_base = checkout_path if checkout_path else CHECKOUT_PATH

        # 2. Locate specific project directory
        _buggy_str = f"{pid}_{bid}_buggy"
        current_checkout_path = os.path.join(_checkout_base, _buggy_str)

        # 3. Dynamically determine log file names (saved in project directory)
        bug_detect_log = os.path.join(self.base_dir, f"bugDetect_{pid}_{bid}_{test_method.replace('::', '_')}.log")
        bug_detect_ori_log = os.path.join(self.base_dir,
                                          f"bugDetectOri_{pid}_{bid}_{test_method.replace('::', '_')}.log")
        failing_tests_path = os.path.join(self.base_dir, "failing_tests")

        # Store log paths for subsequent raw_debug_info reading
        self._bug_detect_log = bug_detect_log
        self._bug_detect_ori_log = bug_detect_ori_log

        if not os.path.exists(current_checkout_path):
            print(f"[ERROR] Project {current_checkout_path} not found. Skipping...")
            return "error"

        # 4. Critical: configuration file temp.properties must be placed in the current test execution project root directory
        # So that -javaagent=...="./temp.properties" in the ant script can read it correctly
        temp_properties = os.path.abspath(os.path.join(current_checkout_path, "temp.properties"))

        # 5. Clean up old traces
        try:
            files_to_clean = [bug_detect_log, bug_detect_ori_log, failing_tests_path,
                              f"{bug_detect_log}.1", f"{bug_detect_ori_log}.1", temp_properties]
            for file in files_to_clean:
                if os.path.exists(file):
                    os.remove(file)
        except Exception as e:
            print(f"[WARNING] Failed to clean old logs: {str(e)}")

        # 6. Write current dynamic configuration
        try:
            with open(temp_properties, "w") as f:
                f.write(f"{KEY_ARGS_USE_SPECIFIED}=true\n")
                f.write(f"{KEY_ARGS_METHODS}={methods_located}\n")
                # Must use absolute paths to ensure Java Agent can accurately find the write location
                f.write(f"log.file.path={os.path.abspath(bug_detect_log)}\n")
                f.write(f"ori.log.file.path={os.path.abspath(bug_detect_ori_log)}\n")
        except Exception as e:
            print(f"[ERROR] Failed to write temp.properties: {str(e)}")
            return "error"

        # 7. Assemble Defects4J command
        if single_test:
            cmd = f"{_d4j_exec} test -t {single_test}"
        elif relevant:
            cmd = f"{_d4j_exec} test -r"
        else:
            cmd = f"{_d4j_exec} test"

        # 8. Execute test process
        try:
            env = os.environ.copy()
            # Inject configuration path into environment variables for ant script recognition
            env["TEMP_PROPERTIES"] = temp_properties

            print(f"[EXEC] Running: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                cwd=self.base_dir,
                text=True,
                env=env
            )
            stdout = result.stdout
            stderr = result.stderr
        except Exception as e:
            print(f"[ERROR] Subprocess failed: {str(e)}")
            traceback.print_exc()
            return "error"

        # 9. Fault tolerance: if instrumentation fails to generate logs, save console output to log file
        has_trace_log = os.path.exists(bug_detect_log) and os.path.getsize(bug_detect_log) > 0
        has_ori_log = os.path.exists(bug_detect_ori_log) and os.path.getsize(bug_detect_ori_log) > 0

        # Modified logic: only fallback to stdout/stderr when neither log is generated
        if not has_trace_log and not has_ori_log:
            print(
                f"[INFO] No instrumentation logs found ({bug_detect_log} or {bug_detect_ori_log}). Falling back to stdout/stderr.")
            try:
                # Write stdout to log file only on complete failure for troubleshooting
                with open(bug_detect_log, "w") as f:
                    f.write("=== stdout ===\n")
                    f.write(stdout)
                    f.write("\n=== stderr ===\n")
                    f.write(stderr)
            except Exception as e:
                print(f"Failed to write fallback log: {str(e)}")

        # Optional: if successful, print a hint here
        # else:
        #     print(f"[SUCCESS] Instrumentation logs generated.")

        return "success"

    def raw_debug_info(self):
        _result = ""

        # Read dynamic log file
        if self._bug_detect_log and os.path.exists(self._bug_detect_log):
            with open(self._bug_detect_log, "r") as f:
                _result = f.read()
            if os.path.getsize(self._bug_detect_log) < 5 * 1024:
                _last_debug_file = f"{self._bug_detect_log}.1"
                if os.path.exists(_last_debug_file):
                    with open(_last_debug_file, "r") as f:
                        _result += f.read()

        # If _bug_detect_log is empty, try reading _bug_detect_ori_log
        if len(_result) == 0 and self._bug_detect_ori_log and os.path.exists(self._bug_detect_ori_log):
            with open(self._bug_detect_ori_log, "r") as f:
                _result = f.read()
            if os.path.getsize(self._bug_detect_ori_log) < 5 * 1024:
                _last_debug_file = f"{self._bug_detect_ori_log}.1"
                if os.path.exists(_last_debug_file):
                    with open(_last_debug_file, "r") as f:
                        _result += f.read()

        # Extract failing_tests summary information, only add to the very beginning
        summary_header = ""
        failing_tests_path = os.path.join(self.base_dir, D4J_FAILING_TEST)
        if os.path.exists(failing_tests_path):
            try:
                with open(failing_tests_path, "r") as f:
                    lines = f.readlines()
                    for i in range(len(lines) - 1):
                        line = lines[i].strip()
                        if line.startswith("--- ") and "::" in line:
                            exception_line = lines[i + 1].strip()
                            summary_header = f"Exception: {exception_line}\n\n"
                            break
            except Exception:
                traceback.print_exc()

        return summary_header + _result