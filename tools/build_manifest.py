#!/usr/bin/env python3
"""
Build manifest.json for the research-figs viewer.

Walks the repository, parses parameters out of directory names and filenames,
and writes a compact manifest that index.html reads to populate its menus.

Usage:
    python build_manifest.py                # run from the repo root
    python build_manifest.py --root /path/to/research-figs

Filename / directory conventions understood:
    <family>/<checkpoint>/n<N>/..._n<N>_b<beta>_p<i>.png     (imi_profiles, dcont_histograms)
    <family>/n<N>/..._n<N>_c<k>_p<i>.png                     (genweights_ridge)
    <family>/anything.png                                    (rate_distance, no parameters)

Anything else that ends in .png/.svg/.jpg is still indexed; it just shows up
with whatever parameters could be parsed (possibly none).
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone

# --- edit these to change how things are labelled in the viewer -------------

# c0 / c1 / c2 / c3 in the genweights filenames, in order.
# Must match the checkpoint directory names used by the other families.
CHECKPOINT_ORDER = ["O1", "Ologn", "On", "Onz"]

CHECKPOINT_LABELS = {
    "O1": "O(1)",
    "Ologn": "O(log n)",
    "On": "O(n)",
    "Onz": "O(n^z)",
}

FAMILY_LABELS = {
    "imi_profiles": "I(A:R) profiles",
    "imi_profiles_symlog": "I(A:R) profiles \u2014 symlog",
    "dcont_histograms": "Contiguous distance P(d*)",
    "genweights_ridge": "Generator weights \u2014 ridgeline",
    "genweights_ridge_symlog": "Generator weights \u2014 ridgeline, symlog",
    "rate_distance": "Rate\u2013distance landscapes",
}

# Optional: map the p index in filenames to the actual measurement rate.
# Leave empty to display the raw index. Example:
#   P_VALUES = {"imi_profiles": [0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.23, 0.26, 0.29, 0.32]}
P_VALUES = {}

IMAGE_EXT = (".png", ".svg", ".jpg", ".jpeg", ".webp")
AXIS_ORDER = ["checkpoint", "n", "beta", "p"]

# ---------------------------------------------------------------------------

RE_N_DIR = re.compile(r"^n(\d+)$")
RE_N_FILE = re.compile(r"_n(\d+)(?=[_.])")
RE_BETA = re.compile(r"_b([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)(?=[_.])")
RE_P = re.compile(r"_p(\d+)(?=[_.])")
RE_C = re.compile(r"_c(\d+)(?=[_.])")


def parse_figure(relpath):
    """Turn 'imi_profiles/O1/n32/imi_profile_n32_b0.01_p3.png' into a record."""
    parts = relpath.split("/")
    family, dirs, filename = parts[0], parts[1:-1], parts[-1]
    params = {}

    for d in dirs:
        m = RE_N_DIR.match(d)
        if m:
            params["n"] = int(m.group(1))
        else:
            params["checkpoint"] = d

    m = RE_N_FILE.search(filename)
    if m:
        params["n"] = int(m.group(1))
    m = RE_BETA.search(filename)
    if m:
        params["beta"] = m.group(1)          # kept as a string so it stays exact
    m = RE_P.search(filename)
    if m:
        params["p"] = int(m.group(1))
    m = RE_C.search(filename)
    if m and "checkpoint" not in params:
        k = int(m.group(1))
        params["checkpoint"] = (
            CHECKPOINT_ORDER[k] if k < len(CHECKPOINT_ORDER) else f"c{k}"
        )

    return family, params


def build(relpaths):
    families = {}
    for relpath in sorted(relpaths):
        if not relpath.lower().endswith(IMAGE_EXT):
            continue
        family, params = parse_figure(relpath)
        fam = families.setdefault(family, {"axes": set(), "figures": []})
        fam["axes"].update(params)
        fam["figures"].append((params, relpath))

    out = []
    for family in sorted(families):
        fam = families[family]
        axes = [a for a in AXIS_ORDER if a in fam["axes"]]
        rows = []
        for params, relpath in fam["figures"]:
            rows.append([params.get(a) for a in axes] + [relpath])
        out.append(
            {
                "id": family,
                "label": FAMILY_LABELS.get(family, family.replace("_", " ")),
                "fields": axes + ["path"],
                "rows": rows,
            }
        )

    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "checkpointLabels": CHECKPOINT_LABELS,
        "pValues": P_VALUES,
        "families": out,
    }


def walk(root):
    skip = {".git", ".github", "node_modules", "tools"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if "/" in rel:  # ignore loose files at the repo root
                yield rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--out", default=None, help="output path (default: <root>/manifest.json)")
    args = ap.parse_args()

    manifest = build(walk(args.root))
    out = args.out or os.path.join(args.root, "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))

    total = sum(len(f["rows"]) for f in manifest["families"])
    print(f"wrote {out}: {total} figures across {len(manifest['families'])} families")
    for fam in manifest["families"]:
        print(f"  {fam['id']:<26} {len(fam['rows']):>5}  axes: {', '.join(fam['fields'][:-1]) or '(none)'}")


if __name__ == "__main__":
    main()
