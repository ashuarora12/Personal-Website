"""Scores the rule-based indicator classifier against the manually coded validation samples."""
import sys
from math import sqrt
import pandas as pd

def wilson(x, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = x / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))

def score(path, rule_col="rule_type"):
    t = pd.read_csv(path)
    acc = (t[rule_col] == t.manual_type).mean()
    cats = sorted(set(t[rule_col]) | set(t.manual_type))
    pe = sum((t[rule_col] == c).mean() * (t.manual_type == c).mean() for c in cats)
    out = {"n": len(t), "accuracy": round(acc, 3), "kappa": round((acc - pe) / (1 - pe), 3)}
    for c in ["outcome", "output", "reach"]:
        tp = int(((t[rule_col] == c) & (t.manual_type == c)).sum())
        npred, ntrue = int((t[rule_col] == c).sum()), int((t.manual_type == c).sum())
        out[c] = {"tp": tp, "predicted": npred, "true": ntrue,
                  "precision": round(tp / npred, 3) if npred else None, "precision_ci": wilson(tp, npred),
                  "recall": round(tp / ntrue, 3) if ntrue else None, "recall_ci": wilson(tp, ntrue),
                  "manual_share": round(ntrue / len(t), 3), "rule_share": round(npred / len(t), 3)}
    return t, out

if __name__ == "__main__":
    t, out = score(sys.argv[1] if len(sys.argv) > 1 else "validation/test_sample_coded.csv")
    print(pd.crosstab(t.rule_type, t.manual_type, margins=True))
    for k, v in out.items():
        print(k, v)
