#!/usr/bin/env python3
"""logmine.py: what do you ask your assistant for?  Classify the user
prompts in Claude Code transcripts (jsonl) by editing intent.  The
counts in the tab paper's 'What the logs say' came from here; run it
on your own logs to audit your own practice.
usage: python3 logmine.py [transcript_dir]   (default ~/.claude/projects)
"""
import sys, os, json, glob, re, collections

PATS = {
 "rename/uniformity": r"==>|rename|name|uniform|style|together|before|order",
 "interrogate":       r"^why|^what|surely|looks like|is .* used|do we need",
 "verify":            r"test|golden|assert|same speed|runtime|secs|baseline",
 "minimize":          r"\bloc\b|shorter|fold|fossil|delete|drop|get rid|prune",
 "benchmark":         r"lgbm|tabpfn|gbm|compare|versus|vs\b|baseline",
 "deliver-faster":    r"deadline|ship it|quick hack|asap|good enough",
}

def prompts(d):
  for f in glob.glob(os.path.join(d, "*", "*.jsonl")):
    for line in open(f, errors="ignore"):
      if '"type":"user"' not in line: continue
      try: c = json.loads(line)["message"]["content"]
      except (KeyError, json.JSONDecodeError): continue
      if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c
                     if isinstance(x, dict) and x.get("type") == "text")
      if isinstance(c, str):
        c = c.strip()
        if c and c[0] != "<":                   # skip tool noise
          yield os.path.basename(os.path.dirname(f)), c

def main(d):
  hits, projs, n = collections.Counter(), collections.Counter(), 0
  for proj, txt in prompts(d):
    n += 1; projs[proj] += 1
    for k, p in PATS.items():
      if re.search(p, txt.lower()): hits[k] += 1
  print(f"prompts: {n}")
  for k, v in hits.most_common(): print(f"  {v:5d}  {k}")
  print("top projects:")
  for p, v in projs.most_common(5): print(f"  {v:5d}  {p}")

if __name__ == "__main__":
  main(sys.argv[1] if len(sys.argv) > 1 else
       os.path.expanduser("~/.claude/projects"))
