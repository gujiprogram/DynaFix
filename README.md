# DynaFix: Iterative Automated Program Repair Driven by Execution-Level Dynamic Information

[![arXiv](https://img.shields.io/badge/arXiv-2512.24635-b31b1b.svg)](https://arxiv.org/abs/2512.24635)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

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

## 💻 Usage

### 1. Configuration
Before running, create a `.env` file in the root directory and configure your API keys and Defects4J path:

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
DEFECTS4J_HOME=/path/to/defects4j
```


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
