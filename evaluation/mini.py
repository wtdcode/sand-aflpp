#!/usr/bin/python3
from argparse import ArgumentParser
from pathlib import Path
import os
import subprocess
import sys
import threading
import multiprocessing
import queue
import re
import tempfile
unifuzz_programs = [
    #id, prog, commandline, seed_folder
    [1, "exiv2", "@@", "jpg"],
    [2,"tiffsplit","@@","tiff"],
    [3,"mp3gain","@@","mp3"],
    [4,"wav2swf","-o /dev/null @@","wav"],
    [5,"pdftotext","@@ /dev/null","pdf"],
    [6,"infotocap","-o /dev/null @@","text"],
    [7,"mp42aac","@@ /dev/null","mp4"],
    [8,"flvmeta","@@","flv"],
    [9,"objdump","-S @@","obj"],
    [14, "tcpdump", "-e -vv -nr @@", "tcpdump100"],
    [15, "ffmpeg", "-y -i @@ -c:v mpeg4 -c:a copy -f mp4 /dev/null", "ffmpeg100"],
    [16, "gdk-pixbuf-pixdata", "@@ /dev/null", "pixbuf"],
    [17, "cflow", "@@", "cflow"],
    [18, "nm", "-A -a -l -S -s --special-syms --synthetic --with-symbol-versions -D @@", "nm"],
    [19, "sqlite3", "", "sql"],
    [20, "lame", "--quiet @@ /dev/null", "lame3.99.5"],
    [21, "jhead", "@@", "jhead"],
    [22, "imginfo", "-f @@", "imginfo"],
    [23, "jq", ". @@", "json"],
    [24, "mujs", "@@", "mujs"],
]

def mini_one(core:int, fuzz_dir: str, output: str, repeat: int, verbose: bool, folder: str):
    program = fuzz_dir.split("+")[0].strip()
    fuzz_output = Path(output) / fuzz_dir / "default"
    crash_dir = Path(output) / fuzz_dir / "default" / folder

    program_args = None
    envs = os.environ.copy()
    for t in unifuzz_programs:
        if program == t[1]:
            program_args = t[2].split(" ")
    only_asan = ["cflow", "lame", "jq"]
    only_asanubsan = ["exiv2", "flvmeta", "ffmpeg", "gdk-pixbuf-pixdata", "sqlite3"]
    if program in only_asanubsan:
        seq = "ua"
    elif program in only_asan:
        seq = "a"
    else:
        seq = "uam"
    if program == "wav2swf":
        to_rename = []
        for crash in os.listdir(crash_dir):
            crash_path = crash_dir / crash
            if len(crash_path.suffix) == 0 and "id:" in crash_path.name:
                new_path = crash_dir / f"{crash}.wav"
                to_rename.append((crash_path.absolute(), new_path.absolute()))
                os.rename(crash_path.absolute(), new_path.absolute())
            seq = "amu"
        envs["MSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:print_stacktrace=1:allocator_may_return_null=1"
        envs["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:detect_leaks=0:print_stacktrace=1:allocator_may_return_null=1" # ignore oom because objdump handles it already
    if program == "tcpdump":
        with open("/tmp/ubsan.supp", "w+") as f:
            f.write("alignment:*\n")
        envs["UBSAN_OPTIONS"] = "suppressions=/tmp/ubsan.supp:halt_on_error=1:abort_on_error=1:print_stacktrace=1"
        envs["MSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:print_stacktrace=1:allocator_may_return_null=1"
        envs["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:detect_leaks=0:print_stacktrace=1:allocator_may_return_null=1" # ignore oom because objdump handles it already
    
    # https://sqlite.org/forum/forumpost/006d569c84
    if program == "sqlite3":
        with open("/tmp/ubsan.supp", "w+") as f:
            f.write("signed-integer-overflow:*\n")
        envs["UBSAN_OPTIONS"] = "suppressions=/tmp/ubsan.supp:halt_on_error=1:abort_on_error=1:print_stacktrace=1;silence_unsigned_overflow=1"
    
    if program in ["objdump", "imginfo", "gdk-pixbuf-pixdata", "tiffsplit"]:
        envs["MSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:print_stacktrace=1:allocator_may_return_null=1"
        envs["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:detect_leaks=0:print_stacktrace=1:allocator_may_return_null=1" # ignore oom because objdump handles it already

    print(f"Trying to minize {crash_dir} for {program}")
    asan = f"/unibench/bin/aflasan_noins/{program}"
    msan = f"/unibench/bin/aflmsan_noins/{program}"
    ubsan = f"/unibench/bin/aflasanubsan_recover/{program}"
    btmin_args = [
        "afl-btmin.py", "--input", str(crash_dir.absolute()),
        "--asan", asan,
        "--msan", msan,
        "--ubsan", ubsan,
        "--sequence", seq]
    if program not in ['tiffsplit', "sqlite3"]:
        btmin_args += ["--no-gdb"]
    if program == "gdk-pixbuf-pixdata":
        btmin_args += ["--timeout", "20"]
    # if program in ['tcpdump']:
    btmin_args += ["--meta"]
    if verbose:
        btmin_args += ["--verbose"]
    if repeat:
        btmin_args += ["--repeat", str(repeat)]
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_output(["taskset", "-c", str(core)] + btmin_args + ["--", f"/unibench/bin/aflasanubsan/{program}"] + program_args, stderr=sys.stderr, env=envs, cwd=d)

def consumer(core: int, q: queue.Queue, args):
    while True:
        fuzz_dir = q.get()
        
        if fuzz_dir is None:
            break

        print(f"Start to minimized {fuzz_dir} on core {core}")
        mini_one(core, fuzz_dir, args.output, args.repeat, args.verbose, args.folder)
    
    
if __name__ == "__main__":
    p = ArgumentParser("minize")
    p.add_argument("--output", type=str, required=True, help="Path to fuzz output")
    p.add_argument("--verbose", default=False, action="store_true", help="Eval debloat")
    p.add_argument("--cmin", default=False, action="store_true", help="AFL cmin firstly")
    p.add_argument("--folder", default="crashes", help="folder name")
    p.add_argument("--filter", default=".*", help="filter")
    p.add_argument("--repeat", help="repaet")
    p.add_argument("--max", type=int, default=multiprocessing.cpu_count(), help="Max number of threads")
    p.add_argument("--cpu", type=int, default=0, help="cpu start index")
    args = p.parse_args()
    
    cnt = int(args.max)
    cpu = int(args.cpu)
    q = queue.Queue()
    ts = []
    for i in range(cpu, cpu + cnt):
        t = threading.Thread(target=consumer, args=(i, q, args))
        t.start()
        ts.append(t)
    
    for fuzz_dir in os.listdir(str(args.output)):
        if re.match(args.filter, fuzz_dir) is None:
            print(f"{fuzz_dir} not matching {args.filter}. skipped")
            continue
        if not ( Path(args.output) / fuzz_dir ).is_file():
            if "+test" not in fuzz_dir and "+r" in fuzz_dir:

                q.put(fuzz_dir)
    
    for i in range(cnt):
        q.put(None)
    
    for t in ts:
        t.join()
