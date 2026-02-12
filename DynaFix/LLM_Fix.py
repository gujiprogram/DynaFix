import argparse
import pandas as pd
from tqdm import tqdm
import threading
from filelock import FileLock
import os
import json
import re
import copy
from dotenv import load_dotenv, find_dotenv
from LLM.llm_interface_gpt4o import LLMInterface
from itertools import islice
from LLM.prompts import *
from validator.defects4j_validator import *
from DebugInfoFetch.ExtractDebugInfo import *
from DebugInfoFetch.Project import *


def read_debug_info(debug_file_path, max_size=50 * 1024, max_lines=300):
    try:
        file_size = os.path.getsize(debug_file_path)

        with open(debug_file_path, 'r', encoding='utf-8') as f:
            if file_size <= max_size:
                content = f.read().strip()
            else:
                content = '\n'.join(line.strip() for line in islice(f, max_lines))

            return content
    except FileNotFoundError:
        return f"Failed to read debug info: File not found"
    except Exception as e:
        return f"Failed to read debug info: {str(e)}"


def read_method_calls(method_calls_file_path, max_size=50 * 1024, max_entries=300):
    try:
        file_size = os.path.getsize(method_calls_file_path)

        with open(method_calls_file_path, 'r', encoding='utf-8') as f:
            if file_size <= max_size:
                data = json.load(f)
            else:
                data = []
                for i, line in enumerate(islice(f, max_entries)):
                    try:
                        entry = json.loads(line.strip())
                        data.append(entry)
                    except json.JSONDecodeError:
                        f.seek(0)
                        full_data = json.load(f)
                        data = full_data[:max_entries]
                        break

        result = ""
        for entry in data:
            result += f"Method: {entry.get('method', 'Unknown')}\n"
            result += f"Comment:\n    {entry.get('doc', 'No comment')}\n"
            result += f"Source Code:\n    {entry.get('code', 'No code')}\n\n"

        return result.strip()
    except FileNotFoundError:
        return f"Failed to read method calls: File not found"
    except json.JSONDecodeError as e:
        return f"Failed to read method calls: Invalid JSON format"
    except Exception as e:
        return f"Failed to read method calls: {str(e)}"


def save_checkpoint(checkpoint_file, current_id):
    """Save current processed ID to checkpoint file"""
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump({'last_id': current_id}, f)


def load_checkpoint(checkpoint_file):
    """Load last processed ID from checkpoint file"""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_id', 0)
    return 0


def get_exception_info(msg_data, slug):
    """Get exception_info for specified slug from msg_data"""
    try:
        row = msg_data[msg_data['slug'] == slug]
        if not row.empty:
            return row['exception_info'].iloc[0].strip()
        return "No exception info available"
    except Exception as e:
        return f"Failed to read exception info: {str(e)}"


def merge_samples(samples):
    """Merge duplicate buggy_code samples (inline standardization logic)"""
    if not samples:
        return samples

    standardized = {}
    for sample in samples:
        buggy_code = sample['buggy_code'].strip()
        lines = [line.strip() for line in buggy_code.strip().split("\n") if line.strip()]
        key = " ".join(" ".join(lines).split())
        if key not in standardized:
            standardized[key] = sample

    return list(standardized.values())


def build_prompt(args, samples, msg_data, width, iteration, pid, bid):
    """Construct prompt based on mode, select debug info source based on iteration"""
    slug = samples[0]['slug']
    prompt = []

    buggy_codes = [sample['buggy_code'].strip() for sample in samples]
    buggy_code_str = "\n\n".join([f"// Method {i + 1}\n{code}" for i, code in enumerate(buggy_codes)])

    if iteration == 0:
        debug_file_path = os.path.join(args.debug_info_dir, f"{slug}b.txt")
        method_calls_file_path = os.path.join(args.method_calls_dir, f"{slug}b_method_calls.json")
    else:
        debug_file_path = os.path.join(args.dynamic_output_path, "DebugInfo",
                                       f"{pid}_{bid}_width{width}_iter{iteration}.txt")
        method_calls_file_path = os.path.join(args.dynamic_output_path, "MethodCalls",
                                              f"{pid}_{bid}_iter{iteration}_method_calls.json")

    if args.mode == 'debuginfo':
        prompt = copy.deepcopy(HISTORY_DEBUG_D4J)
        debug_info = read_debug_info(debug_file_path)
        method_calls = read_method_calls(method_calls_file_path)

        query = DEBUG_PROMPT
        query = query.replace("{BUGGY_CODE}", buggy_code_str)
        query = query.replace("{DEBUG_INFO}", debug_info)
        query = query.replace("{CALL_INFO}", method_calls)
    elif args.mode == 'pure':
        prompt = copy.deepcopy(HISTORY_PURE_D4J)
        query = USER_PROMPT
        query = query.replace("{BUGGY_CODE}", buggy_code_str)
    elif args.mode == 'exception':
        prompt = copy.deepcopy(HISTORY_EXCEPTION_D4J)
        exception_info = get_exception_info(msg_data, slug)
        query = EXCEPTION_PROMPT
        query = query.replace("{BUGGY_CODE}", buggy_code_str)
        query = query.replace("{EXCEPTION_INFO}", exception_info)
    else:
        raise ValueError("mode must be 'debuginfo', 'pure', or 'exception'")

    prompt.append({"role": "user", "content": query})
    return prompt


def save_response_record(slug, width_attempt, iteration, prompt, response):
    """Save records of prompt and response"""
    record_dir = os.path.join('result/defects4j', args.remote_model + '_' + args.mode + '_' + 'records_GPT4o')
    if not os.path.exists(record_dir):
        os.makedirs(record_dir)

    pid, bid = slug.rsplit('_', 1)
    record_file = os.path.join(record_dir, f"{pid}_{bid}_width{width_attempt}_iter{iteration}.txt")

    with open(record_file, 'w', encoding='utf-8') as f:
        f.write("==== Prompt ====\n")
        f.write(json.dumps(prompt, indent=2))
        f.write("\n\n==== Response ====\n")
        f.write(response)


def debug(args):
    if not os.path.exists('result/defects4j'):
        os.makedirs('result/defects4j')

    checkpoint_file = os.path.join('result/defects4j', f'checkpoint_{args.mode}_gpt4o.json')

    data = pd.read_csv(args.data_path, sep=',', encoding='utf-8', engine='python')
    msg_data = pd.read_csv(args.msg_path, sep=',', encoding='utf-8', engine='python')

    grouped_data = data.groupby('slug')
    unique_slugs = list(grouped_data.groups.keys())

    total_unique = len(unique_slugs)
    print(f"Total number of unique slugs: {total_unique}")

    if os.path.exists(args.result_path):
        df_results = pd.read_csv(args.result_path, sep=',', encoding='utf-8', engine='python')
    else:
        df_results = pd.DataFrame(columns=['ID', 'slug', 'bug', 'fix', 'width_attempt', 'iteration'])

    if os.path.exists(args.eval_path):
        df_eval = pd.read_csv(args.eval_path, sep=',', encoding='utf-8', engine='python')
    else:
        df_eval = pd.DataFrame(columns=['ID', 'slug', 'reward', 'submission_result', 'width_attempt', 'iteration'])

    row_num = load_checkpoint(checkpoint_file)
    print(f"Resuming from ID: {row_num}")

    debugger = LLMInterface(args.api_key, args.remote_model)

    for i, slug in tqdm(enumerate(unique_slugs), total=len(unique_slugs), initial=row_num):
        if i < row_num:
            continue

        samples = grouped_data.get_group(slug).to_dict('records')
        samples = merge_samples(samples)
        pid, bid = slug.rsplit('_', 1)
        deep_patch_history = []
        width_patch_history = []
        repair_success = False
        eval_index = len(df_eval)

        for width_attempt in range(args.width_try):
            if repair_success:
                break

            print(f"[INFO] Start width attempt {width_attempt + 1}/{args.width_try} for slug {slug}")
            last_fixed_codes = [sample['buggy_code'].strip() for sample in samples]
            deep_patch_history = []

            try:
                j = 0
                prompt = build_prompt(args, samples, msg_data, width_attempt, j, pid, bid)

                if width_patch_history:
                    history_patches_str = "\n\n".join([msg["content"] for msg in width_patch_history])
                    prompt[-1]["content"] = (
                                                "You are performing breadth-based program repair, where each attempt "
                                                "should try a different strategy to fix the bug. Your goal is to "
                                                "propose a patch that changes the actual program logic and has a "
                                                "meaningful chance of resolving the issue.\n\n "
                                                "Do NOT make cosmetic changes such as modifying comments, reformatting code, or adjusting error messages — these are not valid fixes.\n"
                                                "Avoid repeating any previous fix exactly, even with minor rewording or refactoring. Repetition wastes exploration.\n"
                                                "Think diversely: Your new patch should be different in its repair logic. \n"
                                                "Below are previous fix attempts in this breadth search. Study them to avoid overlap and improve diversity:\n\n"
                                                f"{history_patches_str}\n"
                                                "The following is the original buggy code and its debugging information. "
                                                "Use this information to guide your fix:\n"
                                            ) + prompt[-1][
                                                "content"] + "Output only the fixed functions in a single code block, with each function preceded by a comment `// Fixed Method X` (where X is the method number). Do not include any other text or explanations."

                response = debugger.chat(prompt, i, slug, max_retries=10, temperature=args.temperature)

                # Save prompt and response records
                save_response_record(slug, width_attempt, j, prompt, response)

                pattern = r"```.*?\n(.*?)```"
                pattern2 = r"(?:// Fixed Method \d+\n.*?)(?=(?:// Fixed Method \d+\n|$))"
                codeblocks_1 = re.findall(pattern, response, flags=re.DOTALL)
                codeblocks_2 = re.findall(pattern2, response, flags=re.DOTALL)

                if not codeblocks_1 and not codeblocks_2:
                    print(f"[WARNING] ID {i}, width attempt {width_attempt}, iteration {j} No code block")
                    fixed_codes = ['Match failed'] * len(samples)
                else:
                    if not codeblocks_1 and codeblocks_2:
                        # Markdown not matched, but comment style matched
                        code_content = response
                    else:
                        code_content = codeblocks_1[0].strip()
                    pattern = r'(?:// Fixed Method \d+\n.*?)(?=(?:// Fixed Method \d+\n|$))'
                    fixed_codes = [code.strip() for code in re.findall(pattern, code_content, re.DOTALL) if
                                   code.strip()]
                    fixed_codes = [re.sub(r'^// Fixed Method \d+\n', '', code).strip() for code in fixed_codes]
                    if len(fixed_codes) != len(samples):
                        print(
                            f"[WARNING] ID {i}, width attempt {width_attempt}, iteration {j}: Mismatch in number of fixed methods, expected {len(samples)}, actual {len(fixed_codes)}")
                        fixed_codes = ['Match failed'] * len(samples)

                file_replacements = {}
                for idx, (sample, fixed_code) in enumerate(zip(samples, fixed_codes)):
                    class_path = sample['class_path']
                    buggy_code = sample['buggy_code'].strip()
                    if class_path not in file_replacements:
                        file_replacements[class_path] = []
                    file_replacements[class_path].append((buggy_code, fixed_code))

                reward, submission_result = test(slug, file_replacements, base_dir=args.base_dir)
                print("Test result:", submission_result)
                history_msg = (
                    f"[Iteration {j}] Attempted fix:\n{response.strip()}\n"
                    f"[Iteration {j}] Test result: {submission_result}"
                )
                deep_patch_history.append({"role": "system", "content": history_msg})

                width_history_msg = (
                    f"[Width Attempt {width_attempt}] Attempted fix:\n{response.strip()}\n"
                    f"[Width Attempt {width_attempt}] Test result: {submission_result}"
                )
                width_patch_history.append({"role": "system", "content": width_history_msg})

                for idx, (sample, fixed_code) in enumerate(zip(samples, fixed_codes)):
                    result_idx = len(df_results)
                    df_results.loc[result_idx] = {
                        'ID': i,
                        'slug': sample['slug'],
                        'bug': sample['buggy_code'],
                        'fix': fixed_code,
                        'width_attempt': width_attempt,
                        'iteration': j
                    }
                df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)

                df_eval.loc[eval_index] = {
                    'ID': i,
                    'slug': slug,
                    'reward': reward,
                    'submission_result': submission_result,
                    'width_attempt': width_attempt,
                    'iteration': j
                }
                eval_index += 1  # Increment index
                df_eval.to_csv(args.eval_path, sep=',', encoding='utf-8', index=False)

                save_checkpoint(checkpoint_file, i + 1)

                if 'Compile failed' in submission_result:
                    print(f"[INFO] ID {i}, width attempt {width_attempt}, iteration {j} compile failed, abandoning this width attempt")
                    continue

                if "Time out" in submission_result:
                    print(
                        f"[FATAL] Time out detected at ID {i}, iteration {j}, stopping further attempts.")
                    break

                elif 'Failing tests:' in submission_result:
                    try:
                        failing_count = int(submission_result.split('Failing tests:')[1].strip().split()[0])
                    except Exception:
                        print(f"[ERROR] ID {i}, width attempt {width_attempt}, iteration {j} unable to parse Failing tests count, abandoning this width attempt")
                        break

                    if failing_count == 0:
                        print(f"[SUCCESS] ID {i}, width attempt {width_attempt}, iteration {j} repair successful")
                        repair_success = True
                        break
                    else:
                        # try:
                        #     replace_ant_and_extract_debug_info(pid, bid, width_attempt, j + 1, args)
                        # except Exception as e:
                        #     print(
                        #         f"Thread {threading.get_ident()} error during ant replacement or debug info extraction: {str(e)}")

                        last_fixed_codes = fixed_codes
                        print(f"[INFO] ID {i}, width attempt {width_attempt}, iteration {j} compile success but test failed, starting deep attempt")

                else:
                    print(f"[ERROR] ID {i}, width attempt {width_attempt}, iteration {j} unknown status, abandoning this width attempt")
                    continue

                for j in range(1, args.deep_try):
                    try:
                        current_samples = copy.deepcopy(samples)
                        for idx, code in enumerate(last_fixed_codes):
                            current_samples[idx]['buggy_code'] = code

                        # [Modification 2] Pass current_samples
                        prompt = build_prompt(args, current_samples, msg_data, width_attempt, j, pid, bid)

                        print(f"[INFO] ID {i}, Deep attempt {j}")
                        if deep_patch_history:
                            history_patches_str = "\n\n".join([msg["content"] for msg in deep_patch_history])
                            prompt[-1]["content"] = (
                                                        "You are performing iterative program repair.\n\n"
                                                        "Your task is to **analyze the previous patches and their test outcomes**, understand why they failed, and produce an **improved fix**. \n"
                                                        "Do NOT repeat previous fixes verbatim — this includes identical control flow, clone/add logic, or unchanged loops. Superficial edits (like renaming, formatting, or rephrased error messages) are also unacceptable.\n"
                                                        "Instead, make meaningful changes to the program logic that could plausibly fix the remaining test failures.\n"
                                                        "You may slightly revise the logic structure, change loop boundaries, add filtering, handle special cases, or introduce helper methods to make your fix more robust.\n\n"
                                                        f"{history_patches_str}"
                                                        "The following is the most recent attempted fix and its debugging results. "
                                                        "Use this information to guide your fix:\n"
                                                    ) + prompt[-1][
                                                        "content"] + "Output only the fixed functions in a single code block, with each function preceded by a comment `// Fixed Method X` (where X is the method number). Do not include any other text or explanations."

                        response = debugger.chat(prompt, i, slug, max_retries=10, temperature=args.temperature)

                        # Save prompt and response records
                        save_response_record(slug, width_attempt, j, prompt, response)

                        pattern = r"```.*?\n(.*?)```"
                        pattern2 = r"(?:// Fixed Method \d+\n.*?)(?=(?:// Fixed Method \d+\n|$))"
                        codeblocks_1 = re.findall(pattern, response, flags=re.DOTALL)
                        codeblocks_2 = re.findall(pattern2, response, flags=re.DOTALL)

                        if not codeblocks_1 and not codeblocks_2:
                            print(f"[WARNING] ID {i}, deep attempt {width_attempt}, iteration {j} No code block")
                            fixed_codes = ['Match failed'] * len(current_samples)
                        else:
                            if not codeblocks_1 and codeblocks_2:
                                # Markdown not matched, but comment style matched
                                code_content = response
                            else:
                                code_content = codeblocks_1[0].strip()
                            pattern = r'(?:// Fixed Method \d+\n.*?)(?=(?:// Fixed Method \d+\n|$))'
                            fixed_codes = [code.strip() for code in re.findall(pattern, code_content, re.DOTALL) if
                                           code.strip()]
                            fixed_codes = [re.sub(r'^// Fixed Method \d+\n', '', code).strip() for code in fixed_codes]
                            if len(fixed_codes) != len(current_samples):
                                print(
                                    f"Mismatch in number of fixed methods for ID {i}, iteration {j}: expected {len(current_samples)}, got {len(fixed_codes)}")
                                fixed_codes = ['Match failed'] * len(current_samples)

                        file_replacements = {}
                        for idx, (sample, fixed_code) in enumerate(zip(samples, fixed_codes)):
                            class_path = sample['class_path']
                            buggy_code = sample['buggy_code'].strip()
                            print(
                                f"[INFO] ID {i}, iteration {j}, using buggy_code from: {'last_fixed_codes' if j > 0 else 'sample'}")
                            if class_path not in file_replacements:
                                file_replacements[class_path] = []
                            file_replacements[class_path].append((buggy_code, fixed_code))

                        reward, submission_result = test(slug, file_replacements, base_dir=args.base_dir)

                        history_msg = (
                            f"[Iteration {j}] Attempted fix:\n{response.strip()}\n"
                            f"[Iteration {j}] Test result: {submission_result}"
                        )
                        deep_patch_history.append({"role": "system", "content": history_msg})

                        for idx, (sample, fixed_code) in enumerate(zip(current_samples, fixed_codes)):
                            result_idx = len(df_results)
                            df_results.loc[result_idx] = {
                                'ID': i,
                                'slug': sample['slug'],
                                'bug': sample['buggy_code'],
                                'fix': fixed_code,
                                'width_attempt': width_attempt,
                                'iteration': j
                            }
                        df_results.to_csv(args.result_path, sep=',', encoding='utf-8', index=False)

                        df_eval.loc[eval_index] = {
                            'ID': i,
                            'slug': slug,
                            'reward': reward,
                            'submission_result': submission_result,
                            'width_attempt': width_attempt,
                            'iteration': j
                        }
                        eval_index += 1
                        df_eval.to_csv(args.eval_path, sep=',', encoding='utf-8', index=False)

                        save_checkpoint(checkpoint_file, i + 1)

                        if submission_result != 'Compile failed':
                            last_fixed_codes = [fixed_code if fixed_code != 'Match failed' else last_fixed_codes[idx]
                                                for idx, fixed_code in enumerate(fixed_codes)]

                        if "Locate failed" in submission_result:
                            print(
                                f"[FATAL] Locate failed detected at ID {i}, iteration {j}, stopping further attempts.")
                            break

                        if "Compile failed" in submission_result:
                            print(
                                f"[FATAL] Compile failed detected at ID {i}, iteration {j}, stopping further attempts.")
                            break

                        if "Time out" in submission_result:
                            print(
                                f"[FATAL] Time out detected at ID {i}, iteration {j}, stopping further attempts.")
                            break

                        if not reward and submission_result != 'Compile failed':
                            print(
                                f"Generating new debug info, ID {i}, iteration {j}, thread {threading.get_ident()}, because reward=False and submission_result={submission_result}")
                            # try:
                            #     replace_ant_and_extract_debug_info(pid, bid, width_attempt, j + 1, args)
                            # except Exception as e:
                            #     print(
                            #         f"Thread {threading.get_ident()} error during ant replacement or debug info extraction: {str(e)}")

                        if args.early_stop and reward:
                            repair_success = True
                            print(f"[SUCCESS] ID {i}, iteration {j} repair successful")
                            break

                    except Exception as e:
                        print(f"Error processing ID {i}, try {j}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        save_checkpoint(checkpoint_file, i)
                        continue

            finally:
                print(f"[INFO] Restoring repo for slug {slug} after processing (ID {i})")
                try:
                    success = restore_file(slug, base_dir=args.base_dir)
                    if success:
                        print(f"[INFO] Successfully restored repo for slug {slug}")
                    else:
                        print(f"[WARNING] Failed to restore repo for slug {slug}")
                except Exception as restore_error:
                    print(f"[ERROR] Exception while restoring repo for slug {slug}: {restore_error}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automated bug fixing for Defects4J dataset")
    parser.add_argument('--api_key', default="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", type=str,
                        help="API key for LLM")
    parser.add_argument('--remote_model', default="gpt-4o-2024-11-20", type=str, help="Remote LLM model name")
    parser.add_argument('--data_path',
                        default="./data/test_data/Defects4j_v1.2_single_function/Defects4J_v1.2_single_function.csv",
                        type=str, help="Path to Defects4J code data")
    parser.add_argument('--msg_path', default="./data/defects4j_exception_info.csv", type=str,
                        help="Path to Defects4J metadata")
    parser.add_argument('--debug_info_dir', default="./data/output/DebugInfo", type=str,
                        help="Directory for debug info")
    parser.add_argument('--method_calls_dir', default="./data/output/MethodCalls", type=str,
                        help="Directory for method calls")
    parser.add_argument('--dynamic_output_path', default="./data/dynamic_gpt4o", type=str,
                        help="Directory for debug info")
    parser.add_argument('--result_path', default="./result/defects4j/pred", type=str,
                        help="Path to save prediction results")
    parser.add_argument('--eval_path', default="./result/defects4j/eval", type=str,
                        help="Path to save evaluation results")
    parser.add_argument('--mode', default='pure', type=str, choices=['debuginfo', 'pure', 'exception'],
                        help="Debug mode: debuginfo, pure, or exception")
    parser.add_argument('--base_dir', default="/path/to/defects4j_buggy", type=str,
                        help="Path to save evaluation results")
    parser.add_argument('--input_path', default="./data/input", type=str,
                        help="Path to input method location files")
    parser.add_argument('--checkout_path', default="/path/to/defects4j_buggy", type=str,
                        help="Path to checked-out Defects4J projects")
    parser.add_argument('--major_root', default="/path/to/defects4j/major", type=str,
                        help="Path to Defects4J major root")
    parser.add_argument('--width_try', default=7, type=int, help="Maximum width attempts")
    parser.add_argument('--deep_try', default=5, type=int, help="Maximum deep attempts")
    parser.add_argument('--temperature', default=1.0, type=float, help="LLM temperature for generation")
    parser.add_argument('--early_stop', default=True, type=bool, help="Stop early if repair is successful")
    args = parser.parse_args()

    remote_mode_alias = args.remote_model.split('/')[-1]
    args.result_path = f"{args.result_path}_{remote_mode_alias}_{args.mode}_{args.deep_try}_deep_try_{args.width_try}_width_try.csv"
    args.eval_path = f"{args.eval_path}_{remote_mode_alias}_{args.mode}_{args.deep_try}_deep_try_{args.width_try}_width_try.csv"

    debug(args)