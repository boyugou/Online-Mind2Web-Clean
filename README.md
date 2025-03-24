# Online Mind2Web benchmark
Online Mind2Web Benchmark is a user-centric dataset that includes 300 diverse tasks from 136 popular websites across various domains. We use a novel automatic evaluation (AutoEval) pipeline consisting of three key stages: key point identification, key screenshot identification, and outcome judgment. This pipeline enables relatively reliable and scalable online evaluation.

# Setup Environment
```
conda create -n Online_Mind2Web python=3.11
conda activate Online_Mind2Web
pip install -r requirements.txt
```

# Evaluation
Run the script to do the evaluation.
```bash
bash ./script/eval.sh
```
