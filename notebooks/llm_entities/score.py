"""Score try_variants.py runs against a gold file.

    python3 score.py gold_ratatouille.yaml runs/*.json            # summary table
    python3 score.py gold_ratatouille.yaml runs/generic.json -v    # plus per-sentence detail

Measures (gold levels: primary / secondary / minor; see the gold file):
  primary hit   sentences whose model primaries include a gold primary and no wrong referent
  P recall      gold primaries the model lists as primary
  any recall    gold primary/secondary/minor referents the model lists at any strength
  wrong         model targets that match a referent the gold file marks wrong
  unmatched     model targets that match no referent named for that sentence (check by hand)
"""

import argparse
import json
import re

import yaml

LEVELS = ["primary", "secondary", "minor"]


def match(target, referents, names):
    # key "new": try the referring words first, then the search text ("knife" before "blade tool")
    texts = [target["key"]] if target["key"] != "new" else [target.get("words", ""), target.get("search_for", "")]
    for text in texts:
        text = text.lower().replace("_", " ")
        for name in names:                   # gold order: earlier referents win
            for alias in referents[name]:    # whole words, plural allowed: slice(s), tomato(es)
                if re.search(r"\b" + re.escape(alias) + r"(e?s)?\b", text):
                    return name
    return None


def score(gold, run, verbose):
    refs = gold["referents"]
    order = list(refs)
    tot = dict(sent=0, hit=0, p_gold=0, p_found=0, a_gold=0, a_found=0, wrong=0, unmatched=0, targets=0)
    for g in gold["sentences"]:
        sent = next((s for s in run["sentences"] if s["text"].strip().startswith(g["starts"])), None)
        if sent is None:
            print(f"  (no sentence starting {g['starts']!r} in this run)")
            continue
        named = {n for lvl in LEVELS + ["wrong", "optional"] for n in g.get(lvl, [])}
        found = {}                                           # referent -> strongest model strength
        wrong, unmatched = [], []
        for t in sent["targets"]:
            tot["targets"] += 1
            name = match(t, refs, [n for n in order if n in named])
            if name is None:
                unmatched.append(t)
                continue
            if name in g.get("wrong", []):
                wrong.append((name, t["strength"]))
            if name not in found or LEVELS.index(t["strength"]) < LEVELS.index(found[name]):
                found[name] = t["strength"]
        gp = g.get("primary", [])
        model_primaries = {n for n, s in found.items() if s == "primary"}
        if gp:
            tot["sent"] += 1
            tot["hit"] += bool(model_primaries & set(gp)) and not any(s == "primary" for _, s in wrong)
        tot["p_gold"] += len(gp)
        tot["p_found"] += len(model_primaries & set(gp))
        all_gold = [n for lvl in LEVELS for n in g.get(lvl, [])]
        tot["a_gold"] += len(all_gold)
        tot["a_found"] += sum(n in found for n in all_gold)
        tot["wrong"] += len(wrong)
        tot["unmatched"] += len(unmatched)
        if verbose:
            print(f"\n  {sent['n']} {sent['text'][:70]}")
            print("     model: " + ", ".join(f"{n}={s}" for n, s in found.items()))
            miss = [f"{n}({lvl})" for lvl in LEVELS for n in g.get(lvl, []) if n not in found]
            if miss:
                print("     missing: " + ", ".join(miss))
            if wrong:
                print("     WRONG: " + ", ".join(f"{n}={s}" for n, s in wrong))
            for t in unmatched:
                print(f"     unmatched: [{t['key']}] {t.get('search_for', '')!r} ({t['strength']})")
    return tot


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gold")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    with open(a.gold, encoding="utf-8") as f:
        gold = yaml.safe_load(f)
    rows = []
    for path in a.runs:
        with open(path, encoding="utf-8") as f:
            run = json.load(f)
        label = f"{run['variant']}{' think' if run.get('think') else ''}" \
                f"{' x' + str(run['samples']) if run.get('samples', 1) > 1 else ''}" \
                f"{' text-only' if run.get('frames') == 0 else ''}"
        if a.verbose:
            print(f"\n=== {path} ({label})")
        rows.append((path, label, score(gold, run, a.verbose)))
    print(f"\n{'run':40} {'primary hit':>12} {'P recall':>9} {'any recall':>11} {'wrong':>6} {'unmatched':>10}")
    for path, label, t in rows:
        print(f"{(label + '  ' + path)[:40]:40} {t['hit']:>5}/{t['sent']:<6} {t['p_found']:>4}/{t['p_gold']:<4} "
              f"{t['a_found']:>5}/{t['a_gold']:<5} {t['wrong']:>6} {t['unmatched']:>10}")


if __name__ == "__main__":
    main()
