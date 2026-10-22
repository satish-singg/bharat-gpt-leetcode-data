#!/usr/bin/env python3
"""Fill-in-the-middle (FIM) text transform for the pretraining packer. Pure Python, no dependencies.

A code document is cut at two random CHARACTER positions into prefix / middle / suffix and rewritten so the model learns to produce the middle last:
  PSM:  <|fim_prefix|> prefix <|fim_suffix|> suffix <|fim_middle|> middle
  SPM:  <|fim_prefix|><|fim_suffix|> suffix <|fim_middle|> prefix middle     (the variant that keeps the prompt a contiguous string; both are trained)
Character-level cuts (not token-level) avoid half-tokens at the seams. The transform is applied BEFORE tokenization, with the FIM special tokens added to the tokenizer
(tools/add_fim_tokens.py), and the loss stays on every token, as in StarCoder / Qwen2.5-Coder style training. The packer appends <eos> after the transformed document as usual.

  python3 tools/fim.py --demo        # prints a PSM and an SPM example
Settings used here: rate 0.5 of CODE documents (Bavarian et al. report no penalty for left-to-right quality at 50%), half PSM / half SPM, cut points uniform over characters,
documents under `min_chars` are left alone. Natural-language documents are never transformed (decide by source, see is_code_source)."""
import argparse, random

FIM_PREFIX, FIM_MIDDLE, FIM_SUFFIX, FIM_PAD = "<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>", "<|fim_pad|>"
FIM_TOKENS = (FIM_PREFIX, FIM_MIDDLE, FIM_SUFFIX, FIM_PAD)
CODE_SOURCES_DEFAULT = ("code_python", "code_java_sql_js", "stack_edu", "code_contest", "stack_java_clean", "cs-v5-code")


def is_code_source(source, code_sources=CODE_SOURCES_DEFAULT):
    return any(source == s or source.startswith(s) for s in code_sources)


def fim_transform(text, rng, rate=0.5, spm_rate=0.5, min_chars=64):
    """Return (new_text, mode) with mode in {"none", "psm", "spm"}. `rng` is a random.Random so a build is reproducible."""
    if rng.random() >= rate or len(text) < min_chars:
        return text, "none"
    a, b = sorted((rng.randrange(len(text) + 1), rng.randrange(len(text) + 1)))
    prefix, middle, suffix = text[:a], text[a:b], text[b:]
    if rng.random() < spm_rate:
        return f"{FIM_PREFIX}{FIM_SUFFIX}{suffix}{FIM_MIDDLE}{prefix}{middle}", "spm"
    return f"{FIM_PREFIX}{prefix}{FIM_SUFFIX}{suffix}{FIM_MIDDLE}{middle}", "psm"


def undo(text):
    """Inverse of fim_transform (for tests and for checking packed data): original text, or the text itself if it is not FIM formatted."""
    if not text.startswith(FIM_PREFIX): return text
    body = text[len(FIM_PREFIX):]
    if body.startswith(FIM_SUFFIX):                          # SPM
        rest = body[len(FIM_SUFFIX):]
        suffix, _, pm = rest.partition(FIM_MIDDLE)
        return pm + suffix
    prefix, _, rest = body.partition(FIM_SUFFIX)             # PSM
    suffix, _, middle = rest.partition(FIM_MIDDLE)
    return prefix + middle + suffix


def infill_prompt(prefix, suffix):
    """Inference prompt for completing the gap between prefix and suffix (SPM layout); generation ends at <eos>."""
    return f"{FIM_PREFIX}{FIM_SUFFIX}{suffix}{FIM_MIDDLE}{prefix}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--demo", action="store_true"); a = ap.parse_args()
    if a.demo:
        src = "def add(a, b):\n    total = a + b\n    return total\n"
        for seed in range(20):
            out, mode = fim_transform(src, random.Random(seed), rate=1.0)
            print(f"--- {mode}\n{out!r}")
            if seed >= 3: break


if __name__ == "__main__":
    main()
