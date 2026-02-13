# 📊 Experimental Results

This directory contains the detailed experimental data and logs generated during the evaluation of **DynaFix**. The results are organized by Research Questions (RQs).

## 📂 Directory Contents

* **`Baseline/`**
    * Contains the **lists of bug IDs** fixed by baseline methods (e.g., ReInFix, AlphaRepair, ChatRepair) used for comparison.

* **`RQ1/` (Effectiveness)**
    * Data for **RQ1**.
    * Includes repair results on **Defects4J v1.2 & v2.0**.
    * Covers experiments under both **perfect** and **imperfect** (GZoltar+Ochiai) fault localization settings.

* **`RQ2/` (Generalization & Robustness)**
    * Data for **RQ2**.
    * **Generalization:** Results on the **Real-World Benchmark (RWB)** across different LLM backends.
    * **Robustness:** Results on the **Defects4J-Trans** (code perturbation) benchmark to evaluate resistance to syntactic changes.

* **`RQ3/` (Parameter Sensitivity)**
    * Data for **RQ3**.
    * **Parameter Analysis:** Impact of Search Breadth ($B$) and Depth ($D$) on repair performance.

* **`RQ4/` (Qualitative & Ablation Analysis)**
    * Data for **RQ4**.
    * **Function Granularity:** Comparison of results between single-function and multi-function bugs on Defects4J.
    * **Ablation Study:** Results validating the contribution of different components in DynaFix.
