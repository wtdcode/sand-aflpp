from argparse import ArgumentParser
from pathlib import Path
from typing import NamedTuple
import os
import re
import csv

class Stat(NamedTuple):
    total_exec: int
    asan_exec: int
    msan_exec: int
    bugs: int
    crashes: int
    san_only_crashes: int
    first_bug: int # in milliseconds
    cvg: str
    bug_ratio: int
    repeat: int


def parse_bugs(fuzz_dir: Path, queue: bool):
    cnt = 0
    san_cnt = 0
    tn = 0xFFFFFFFFFFFFFFFF
    bugs = set()
    
    if queue:
        bugs_dirs = [
            Path(fuzz_dir) / "crashes",
            Path(fuzz_dir) / "queue"
        ]
    else:
        bugs_dirs = [
            Path(fuzz_dir) / "crashes",
        ]
    
    for bugs_dir in bugs_dirs:
        bt_folder = Path(bugs_dir) / "backtraces"
        for bt in os.listdir(bt_folder):
            if bt.endswith(".json"):
                content = open(bt_folder / bt).read()
                bugs.add(content)
        
        for fname in os.listdir(bugs_dir):
            
            matches = re.findall(r"time:([\d]+)", fname)
            if len(matches) == 0:
                continue
            cur_time = int(matches[0])

            if cur_time < tn:
                tn = cur_time

            if "+san" in fname:
                san_cnt += 1

            if ( bugs_dir / Path(fname) ).is_file():
                cnt += 1
    if tn == 0xFFFFFFFFFFFFFFFF:
        tn = 0
    return len(bugs), cnt, san_cnt, tn

def parse_stats(fuzz_folder: Path):
    fuzz_name = fuzz_folder.name
    
    if "asan" in fuzz_name or "msan" in fuzz_name or "ubsan" in fuzz_name or "debloat" in fuzz_name:
        queue = False
    else:
        queue = True
    
    bugs, crashes, san_crashes, first_bug = parse_bugs(fuzz_folder / "default", queue=queue)
    asan_bin = False
    msan_bin = False
    asan_exec = None
    msan_exec = None
    total_exec = None
    bug_ratio = None
    cvg = None

    rpt = int(re.findall(r"\+r([\d])", fuzz_folder.name)[0])

    with open(fuzz_folder / "default" / "plot_data", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=",")
        rows = [r for r in rdr]
        bug_ratio = int(rows[-1][13])
    
    with open(fuzz_folder / "default" / "fuzzer_stats", "r") as f:
        for ln in f:
            tks = [tk.strip() for tk in ln.split(":")]
            k = tks[0]
            v = tks[1]

            if k == "execs_done" and not asan_bin and not msan_bin:
                total_exec = int(v)

            if k == "bitmap_cvg":
                cvg = v
            
            if asan_bin and k == "total_execs":
                asan_exec = int(v)
                asan_bin = False
            
            if msan_bin and k == "total_execs":
                msan_exec = int(v)
                msan_bin = False

            if k == "extra_binary" and "asan" in v:
                asan_bin = True

            if k == "extra_binary" and "msan" in v:
                msan_bin = True
            
    if asan_exec is None:
        asan_exec = 0
    
    if msan_exec is None:
        msan_exec = 0
    
    return Stat(total_exec, asan_exec, msan_exec, bugs, crashes, san_crashes, first_bug, cvg, bug_ratio, rpt)


if __name__ == "__main__":
    p = ArgumentParser("data eval")
    p.add_argument("--output", type=str, required=True, help="Path to fuzz output")
    p.add_argument("--check", default=False, action="store_true", help="Check if it has stats")
    args = p.parse_args()

    base_folder = Path(args.output)
    results = []
    singels = []
    for fname in os.listdir(base_folder):
        fuzz_folder = base_folder / Path(fname)
        if not fuzz_folder.is_file():
            if (fuzz_folder / "default" / "fuzzer_stats").exists():
                if "+single" in fuzz_folder.name:
                    singels.append( (fuzz_folder, parse_stats(fuzz_folder)))
                else:
                    results.append( (fuzz_folder, parse_stats(fuzz_folder)) )
            else:
                if args.check:
                    print(f"{fuzz_folder} no stats!")
    
    results.sort(key= lambda t : t[1].repeat)
    results.sort(key= lambda t : t[0])

    singels.sort(key= lambda t : t[1].repeat)
    singels.sort(key= lambda t : t[0])

    if not args.check:
        print("\t".join(["name", "total_exec", "asan_exec", "msan_exec", "bugs", "crashes", "san_only", "first_crash", "coverage", "bug_ratio", "repeat"]))
        for fdr, r in results:
            s = f"{fdr.name}\t"
            s += "\t".join(map(str, r))
            print(s)

        print("\t".join(["name", "total_exec", "asan_exec", "msan_exec", "bugs", "crashes", "san_only", "first_crash", "coverage", "bug_ratio", "repeat"]))
        for fdr, r in singels:
            s = f"{fdr.name}\t"
            s += "\t".join(map(str, r))
            print(s)