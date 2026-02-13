# DynaFix: Iterative Automated Program Repair Driven by Execution-Level Dynamic Information

[![arXiv](https://img.shields.io/badge/arXiv-2512.24635-b31b1b.svg)](https://arxiv.org/abs/2512.24635)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

This repository contains the **official implementation and replication package** for the paper: *"DynaFix: Iterative Automated Program Repair Driven by Execution-Level Dynamic Information"*.

## 📖 Overview

Automated Program Repair (APR) has evolved significantly with Large Language Models (LLMs), yet existing methods often struggle due to their reliance on static code representations, which lack fine-grained execution feedback and are sensitive to syntactic variations. **DynaFix** addresses these limitations by integrating execution-level dynamic information directly into the iterative repair workflow. Utilizing a lightweight instrumentation tool named **ByteTrace**, DynaFix captures runtime variable states, branch paths, and call stacks to provide precise context. This approach mimics human debugging: if a patch fails validation, the system re-executes the program to collect updated execution traces, continuously guiding the LLM’s reasoning and avoiding the blind trial-and-error common in static-only methods.

We evaluated DynaFix on the Defects4J v2.0, Real-World Benchmark (RWB), and Defects4J-Trans benchmarks, where it demonstrated superior effectiveness and robustness. DynaFix correctly repaired **236 bugs** using GPT-4 and **186** with GPT-4o, including 23 unique bugs unresolved by existing baselines. Notably, it exhibits exceptional generalization against syntactic perturbations, outperforming state-of-the-art (SOTA) methods by **15.8%–18.2%** on Defects4J-Trans. Furthermore, DynaFix is highly cost-effective, reducing token consumption by approximately **60%–70%** compared to SOTA approaches, making it a robust and efficient solution for automated program repair.

For more details, please refer to our [arXiv paper](https://arxiv.org/abs/2512.24635).

## 📂 Project Structure

```text
.
├── ByteTrace/                  # 🕵️ Java Instrumentation Tool (Agent)
│   ├── ByteTrace_code/         # Source code (Java/Kotlin implementation)
│   └── ByteTrace.jar           # Pre-compiled Java Agent JAR file
│
├── data/                       # 💾 Datasets and Input/Output Data
│   ├── input/                  # Buggy method locations (Fault Localization)
│   ├── output/                 # Collected dynamic runtime information
│   ├── SBFL/                   # Top-k suspicion lists from SBFL
│   ├── Defects4J/              # Metadata for the standard Defects4J dataset
│   └── Defects4J_trans/        # Metadata for the transformed Defects4J dataset
│
├── DynaFix/                    # 🧠 Core Repair Framework (Python)
│   ├── LLM_Fix.py              # 🚀 Main entry script for executing repair
│   ├── DebugInfoFetch/         # Scripts for Defects4J interaction & trace collection
│   ├── LLM/                    # Interfaces for LLM models (GPT-4o, DeepSeek)
│   ├── validator/              # Logic for test execution and patch validation
│   └── result/                 # Temporary logs for current repair sessions
│
└── Result/                     # 📊 Experimental Results (RQ1-RQ4)

```

## 🛠️ Requirements

To run DynaFix and reproduce the experiments, we recommend the following environment (verified on Ubuntu 20.04):

* **Operating System:** Linux (Ubuntu 20.04 LTS recommended).
* **Java:** OpenJDK 11 (Tested on `11.0.27`).
    * *Note: While the DynaFix framework runs on Java 11, ensure Defects4J is properly configured to handle the target project compilation (often requiring JDK 1.8 compatibility).*
* **Python:** Python 3.10 or higher.
* **Defects4J:** Version 2.0. Please follow the [official installation guide](https://github.com/rjust/defects4j).
* **API Keys:** OpenAI API Key (for GPT-4o) or DeepSeek API Key.

## 🚀 Setup & Execution

### Step 1. Download ByteTrace (Instrumentation Tool)
Download the pre-compiled `ByteTrace.jar` from our [Release Page](#) (or locate it directly in the `ByteTrace/` directory of this repository). Save it to a known path, e.g., `/path/to/ByteTrace.jar`.

### Step 2. Configure ByteTrace in Defects4J
To enable dynamic trace collection, you need to inject ByteTrace as a Java agent into the Defects4J execution environment. 

Navigate to `{Defects4J_HOME}/major/bin/ant` and open the file. **Remember to back up this file first!** Add the `-javaagent` argument to the Java command line as shown below:

```bash
#!/bin/sh
# This is an example of how to add ByteTrace as a java agent in Defects4J

BASE="`dirname $0`/.."
if [ -z "$JAVA_HOME" ]; then
    CMD="java"
else
    CMD="$JAVA_HOME/bin/java"
fi

# Add the "-javaagent" line here pointing to your ByteTrace.jar
$CMD \
    -javaagent:/path/to/ByteTrace.jar \
    -Xverify:none \
    -XX:ReservedCodeCacheSize=256M \
    -XX:MaxPermSize=1G \
    -Djava.awt.headless=true \
    -Xbootclasspath/a:$BASE/config/config.jar \
    -jar $BASE/lib/ant-launcher.jar $*
```
Step 3. Configure Repair ParametersYou can run the repair framework by modifying the default arguments directly in LLM_Fix.py or by passing them via the command line.Below is a detailed explanation of the parameters you need to configure to match your local environment:LLM & API Settings:--api_key: Your LLM API key (e.g., OpenAI or DeepSeek key).--remote_model: The model name to use (default: gpt-4o-2024-11-20).Defects4J Environment Paths:--checkout_path: Directory where Defects4J buggy projects are checked out (e.g., /path/to/defects4j_buggy).--major_root: Path to the Defects4J major directory (e.g., /path/to/defects4j/major).Dataset & Input Paths:--data_path: Path to the Defects4J target dataset CSV (e.g., Defects4J_v1.2_single_function.csv).--msg_path: Path to the exception metadata file (defects4j_exception_info.csv).--input_path: Directory containing the initial buggy method locations (Fault Localization results).Output & Log Directories (ByteTrace & DynaFix):--debug_info_dir: Directory to store the raw debug traces collected by ByteTrace.--method_calls_dir: Directory to store method call sequences.--dynamic_output_path: Directory for parsed dynamic execution info.--result_path: Base path to save the final generated patches (predictions).--eval_path: Base path to save test validation results (plausible/correct stats).Search Strategy (LPR):--width_try: Maximum search breadth $B$ (Default: 7).--deep_try: Maximum search depth $D$ (Default: 5).--mode: The context mode for LLM (pure, debuginfo, or exception).--temperature: LLM sampling temperature (Default: 1.0).--early_stop: Stop the search tree early if a correct patch is found (Default: True).Step 4. Run DynaFixOnce your environment and paths are set, simply run the Python script to start the automated repair process:Bashpython LLM_Fix.py
(Alternatively, you can override default settings via CLI, e.g., python LLM_Fix.py --remote_model gpt-4o --width_try 5)


## 📜 Citation
If you find this work useful for your research, please cite our paper:

```text
@article{huang2025dynafix,
  title={DynaFix: Iterative Automated Program Repair Driven by Execution-Level Dynamic Information},
  author={Huang, Zhili and Xu, Ling and Liu, Chao and Sun, Weifeng and Zhang, Xu and Lei, Yan and Yan, Meng and Zhang, Hongyu},
  journal={arXiv preprint arXiv:2512.24635},
  year={2025}
}
```
