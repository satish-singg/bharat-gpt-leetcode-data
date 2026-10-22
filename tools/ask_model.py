#!/usr/bin/env python3
"""Ask one or more checkpoints some questions and print the answers side by side (greedy by default).  Needs torch + a GPU (pod).

  python3 tools/ask_model.py --tokenizer /workspace/kit/phase0/tok/tokenizer.json \
      --ckpt base350=/workspace/run350/ckpt/ckpt_0013012.pt --ckpt sft350=/workspace/sft_v2_run1/sft_final.pt \
      --out /workspace/ask_out.md                       # default question set
  ... --question "Write a Python function that reverses a linked list." --question "..."   # your own (repeatable)
  ... --questions-file my_questions.txt                 # blocks separated by a line containing only ====

Prompts use the SFT layout "Question: <q>\\n\\nAnswer:\\n". The base model was never trained on it, so its answers show what SFT added."""
import argparse, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT = [
    "Write a Python function that returns the indices of two numbers in a list that add up to a target.",
    "Write a Java method that checks whether a string is a palindrome.",
    "Given an array of integers, find the length of the longest strictly increasing subsequence. Solve this problem in Python.",
    "What are the time and space complexity of this Python solution?\n\n```python\ndef f(nums):\n    nums.sort()\n    return nums[len(nums) // 2]\n```",
    "Explain the difference between a stack and a queue, with one use case for each.",
    "Write a Python function that merges two sorted linked lists. Define ListNode yourself.",
    "Write a Java class that implements an LRU cache with get and put in O(1) time.",
    "What is 17 * 24? Show the steps.",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", required=True); ap.add_argument("--ckpt", action="append", required=True, help="NAME=path (repeatable)")
    ap.add_argument("--question", action="append"); ap.add_argument("--questions-file"); ap.add_argument("--out")
    ap.add_argument("--max-new", type=int, default=300); ap.add_argument("--temperature", type=float, default=0.0)
    a = ap.parse_args()
    qs = list(a.question or [])
    if a.questions_file: qs += [b.strip() for b in open(os.path.expanduser(a.questions_file), encoding="utf-8").read().split("\n====\n") if b.strip()]
    qs = qs or DEFAULT
    sys.path[:0] = [str(ROOT / "phase0"), str(ROOT / "phase0" / "gate")]
    from model_api_fast import FastLM
    lines, answers = [], {}
    for spec in a.ckpt:
        name, _, path = spec.partition("=")
        lm = FastLM(os.path.expanduser(path), os.path.expanduser(a.tokenizer))
        print(f"[{name}: step {lm.step}]", flush=True)
        answers[name] = [lm.generate(f"Question: {q}\n\nAnswer:\n", n=1, max_new=a.max_new, temperature=a.temperature, seed=i)[0] for i, q in enumerate(qs)]
        del lm
    for i, q in enumerate(qs):
        lines += [f"\n## Q{i + 1}\n", "```text", q, "```"]
        for name in answers: lines += [f"\n**{name}**\n", "```text", answers[name][i].rstrip(), "```"]
    text = "\n".join(lines) + "\n"
    print(text)
    if a.out: pathlib.Path(os.path.expanduser(a.out)).write_text(text, encoding="utf-8"); print("saved", a.out)


if __name__ == "__main__":
    main()
