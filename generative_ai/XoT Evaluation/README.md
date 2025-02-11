# Everything of Thoughts (XoT) implementation in DataRobot

Authors: yifu.gu@datarobot.com, greig.bloom@datarobot.com, mitsuo.yamamoto@datarobot.com

## Summary

This accelerator introduces the implementation and evaluation of XoT (Everything of Thoughts) in DataRobot, which is the latest approach to make generative AI "think like humans." In the world of generative AI, various methods (called thought generation) are being researched to help AI acquire more human-like "thinking patterns." In particular, XoT aims to produce more accurate answers by teaching generative AI the "thinking process." There are two main methods to achieve XoT:

* Chain-of-Thought (CoT)[1]: A method of thinking by connecting multiple thoughts like a chain and reasoning through them.

* Retrieval Augmented Thought Tree (RATT)[2]: A method of thinking by expanding multiple possibilities like tree branches and retrieving relevant information from the external knowledge base.

This accelerator explains how to implement these methods. Specifically, it introduces how to set up and compare three types of LLM prompts: direct, Chain-of-Thought, and RATT. "Direct" referring to the well-known "you are a helpful assistant." The accelerator also explains how to conduct performance evaluations using sample datasets, comparing the accuracy and efficiency of each method, and analyze using multiple evaluation metrics.

## Prerequisites

This script uses Pulumi to set up the DataRobot environment. If Pulumi is not already installed, install the CLI by following the instructions [here](https://www.pulumi.com/docs/iac/download-install/). After installing for the first time, restart your terminal and run:

```bash
pulumi login --local  # omit --local to use Pulumi Cloud (requires separate account)
```

## Dataset

Use the RAGBench (CC-BY-4.0) dataset, available [here](https://huggingface.co/datasets/rungalileo/ragbench).

## References

[1] Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. (2023). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. arXiv preprint arXiv:2201.11903.

[2] Zhang, J., Wang, X., Ren, W., Jiang, L., Wang, D., & Liu, K. (2024). RATT: A Thought Structure for Coherent and Correct LLM Reasoning. arXiv preprint arXiv:2406.02746.

[3] Friel, R., Belyi, M., & Sanyal, A. (2025). RAGBench: Explainable Benchmark for Retrieval-Augmented Generation Systems. arXiv preprint arXiv:2407.11005.
