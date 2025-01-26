from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import logging
import multiprocessing

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

unifuzz_programs = [
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
    [20, "lame", "@@ /dev/null", "lame3.99.5"],
    [21, "jhead", "@@", "jhead"],
    [22, "imginfo", "-f @@", "imginfo"],
    [23, "jq", ". @@", "json"],
    [24, "mujs", "@@", "mujs"],
]


if __name__ == "__main__":
    p = ArgumentParser("eval")
    p.add_argument("--image", type=str, required=True, help="Docker image name")
    p.add_argument("--msan", default=False, action="store_true", help="MSAN binary")
    p.add_argument("--asan", default=False, action="store_true", help="ASAN binary")
    p.add_argument("--ubsan", default=False, action="store_true", help="UBSAN binary")
    p.add_argument("--asanubsan", default=False, action="store_true", help="ASAN+UBSAN binary")
    p.add_argument("--asanubsanrecover", default=False, action="store_true", help="UBSAN binary but skipp all errors")
    p.add_argument("--ubsanrecover", default=False, action="store_true", help="UBSAN binary but skipp all errors")
    p.add_argument("--asanrecover", default=False, action="store_true", help="ASAN binary but skipp all errors")
    p.add_argument("--msanrecover", default=False, action="store_true", help="MSAN binary but skipp all errors")
    p.add_argument("--debloat", default=False, action="store_true", help="Eval debloat")
    p.add_argument("--single", default=False, action="store_true", help="Eval single sanitizer")
    p.add_argument("--seconds", default=str(timedelta(hours=4).seconds), help="Fuzzing time limit.")
    p.add_argument("--seeds", type=str, required=True, help="Path to the seeds")
    p.add_argument("--repeat", type=int, default=3, help="Repeat")
    p.add_argument("--output", default=".", help="Output folder")
    p.add_argument("--timeout", default="3000", help="Timeout")
    p.add_argument("--schedule", default="fast", help="AFL schedule")
    p.add_argument("--rng", help="rng seeds")
    p.add_argument("--cpu", default=0, type=int, help="Start of CPU")
    p.add_argument("-D", default=False, action="store_true", help="AFL -D")
    p.add_argument("-d", default=False, action="store_true", help="AFL -d")
    p.add_argument("--gdb", default=False, action="store_true", help="Starts with gdb")
    p.add_argument("--valgrind", default=False, action="store_true", help="Starts with valgrind")
    p.add_argument("--abstraction", default="simplify_trace", type=str, help="abstraction to use")
    p.add_argument('programs', metavar='programs', type=str, nargs='+', help=f'Programs: {",".join([t[1] for t in unifuzz_programs])}')
    args = p.parse_args()

    if args.single:
        modes = [args.msan, args.asan, args.ubsan, args.asanubsan, args.asanrecover, args.ubsanrecover, args.asanubsanrecover, args.msanrecover]

        for idx, m1 in enumerate(modes):
            for m2 in modes[idx+1:]:
                if m1 and m2:
                    print(f"Can't eval both in single eval mode")
                    exit(-1)

    else:
        if not args.msan and not args.asan and not args.debloat and not args.ubsan and not args.asanubsan and not args.msanrecover and not args.ubsanrecover and args.asanrecover and not args.asanubsanrecover:
            print(f"Must specify either msan or asan")
            exit(-1)
    
    if "all" in args.programs:
        programs = unifuzz_programs
    else:
        programs = [
            t for t in unifuzz_programs if t[1] in args.programs
        ]

        valid_programs = [t[1] for t in unifuzz_programs]
        for p in args.programs:
            if p not in valid_programs:
                print(f"Program {p} is not valid")
                exit(-1)


    docker_args = [
        "docker",
        "run",
        "-v", f"{Path(args.seeds).absolute()}:/seeds",
        "-v", f"{Path(args.output).absolute()}:/outputs",
        "-it",
        "--rm",
        "--network=host",
        args.image
    ]

    cpu_count = multiprocessing.cpu_count()
    next_cpu = int(args.cpu) % cpu_count

    only_asan = ["cflow", "lame", "jq"]
    only_asanubsan = ["jq", "cflow", "exiv2", "lame", "flvmeta", "ffmpeg", "gdk-pixbuf-pixdata", "sqlite3"]
    
    for prog in programs:
        if prog in only_asan:
            if args.ubsan or args.asanubsanrecover or args.asanubsan:
                print(f"{prog} is asan only (no ubsan)")
                exit(-1)
            
        if prog in only_asanubsan:
            if args.msan or args.msanrecover:
                print(f"{prog} is asanubsan only (no msan)")
                exit(-1)
    
    for prog in programs:
        for i in range(args.repeat):
            name = prog[1]
            cmds = prog[2].split(' ')
            
            fuzz_name = name

            if args.asan:
                fuzz_name += "+asan"

            if args.ubsan:
                fuzz_name += "+ubsan"

            if args.asanrecover:
                fuzz_name += "+asanrecover"
                
            if args.ubsanrecover:
                fuzz_name += "+ubsanrecover"
                
            if args.asanubsanrecover:
                fuzz_name += "+asanubsanrecover"
            
            if args.asanubsan:
                fuzz_name += "+asanubsan"
        
            if args.debloat:
                fuzz_name += "+debloat"
        
            if args.msan:
                fuzz_name += "+msan"
                
            if args.msanrecover:
                fuzz_name += "+msanrecover"

            if args.single:
                fuzz_name += "+single"
            
            if args.schedule != "fast":
                fuzz_name += f"+{str(args.schedule)}"
            
            if args.D:
                fuzz_name += "+D"
            else:
                fuzz_name += "+d"

            fuzz_name += f"+r{i}"

            screen_args = [
                "screen",
                "-S", fuzz_name,
                "-d",
                "-m"
            ]

            seeds_folder = ( Path("/seeds") / str(prog[3]) ).absolute()
            otuput_foler = ( Path("/outputs") / fuzz_name ).absolute()
            afl_args = [
                "env",
                "AFL_SKIP_CPUFREQ=1",
                "AFL_IGNORE_PROBLEMS=1",
                f"AFL_SAN_ABSTRACTION={args.abstraction}"
            ]

            if args.asanrecover or args.asanubsanrecover:
                afl_args += [
                    f"ASAN_OPTIONS=halt_on_error=0:abort_on_error=1:detect_leaks=0:malloc_context_size=0:symbolize=0:allocator_may_return_null=1:detect_odr_violation=0:handle_segv=0:handle_sigbus=0:handle_abort=0:handle_sigfpe=0:handle_sigill=0"
                ]
                
            if args.ubsanrecover or args.asanubsanrecover:
                afl_args += [
                    f"UBSAN_OPTIONS=halt_on_error=0:abort_on_error=0:malloc_context_size=0:allocator_may_return_null=1:symbolize=0:handle_segv=0:handle_sigbus=0:handle_abort=0:handle_sigfpe=0:handle_sigill=0"
                ]
            
            if args.msanrecover:
                # Cheat AFL MSAN exit code check
                afl_args += [
                    f"MSAN_OPTIONS=exit_code=86:exit_code=1:report_umrs=0:symbolize=0:abort_on_error=1:malloc_context_size=0:allocator_may_return_null=1:msan_track_origins=0:handle_segv=0:handle_sigbus=0:handle_abort=0:handle_sigfpe=0:handle_sigill=0"
                ]

            if args.gdb:
                afl_args += [
                    "gdb",
                    "-ex", "set follow-fork-mode parent",
                    "-ex", "r",
                    "--args"
                ]
            
            if args.valgrind:
                afl_args += [
                    "valgrind",
                    "--tool=memcheck",
                    f"--log-file={Path('/outputs') / f'{fuzz_name}.log'}"
                ]

       
            afl_args += [
                "afl-fuzz",
                "-b", str(next_cpu),
                "-t", str(args.timeout),
                "-V", str(args.seconds),
                "-i", str(seeds_folder),
                "-o", str(otuput_foler),
                "-p", str(args.schedule)
            ]
            
            if args.rng:
                afl_args += ["-s", str(args.rng)]
            
            if args.D:
                afl_args += ["-D"]
            
            if args.d:
                afl_args += ["-d"]

            if not args.single:
                if args.asan:
                    afl_args += [
                        "-a", f"/unibench/bin/aflasan_noins/{name}"
                    ]
                    
                if args.debloat:
                    if args.asanubsan:
                        afl_args += [
                            "-a", f"/unibench/bin/debloat/aflasanubsan_noins/{name}"
                        ]
                    else:
                        afl_args += [
                            "-a", f"/unibench/bin/debloat/aflasan_noins/{name}"
                        ]
                
                if args.msan:
                    afl_args += [
                        "-a", f"/unibench/bin/aflmsan_noins/{name}"
                    ]
                    
                if args.ubsan:
                    afl_args += [
                        "-a", f"/unibench/bin/aflubsan_noins/{name}"
                    ]
                    
                if args.asanubsan:
                    afl_args += [
                        "-a", f"/unibench/bin/aflasanubsan_noins/{name}"
                    ]
                
                if args.asanrecover:
                    afl_args += [
                        "-a", f"/unibench/bin/aflasan_recover/{name}"
                    ]
                    
                if args.ubsanrecover:
                    afl_args += [
                        "-a", f"/unibench/bin/aflubsan_recover/{name}"
                    ]
                
                if args.asanubsanrecover:
                    afl_args += [
                        "-a", f"/unibench/bin/aflasanubsan_recover/{name}"
                    ]
                    
                if args.msanrecover:
                    afl_args += [
                        "-a", f"/unibench/bin/aflmsan_recover/{name}"
                    ]

                

                afl_args += [
                    "--",
                    f"/unibench/bin/justafl/{name}",
                ]
            else:
                if args.asan:
                    if args.debloat:
                        afl_args += [
                            "--",
                            f"/unibench/bin/debloat/aflasan/{name}"
                        ]
                    else:
                        afl_args += [
                            "--",
                            f"/unibench/bin/aflasan/{name}"
                        ]
                elif args.debloat:
                    if args.asanubsan:
                        afl_args += [
                            "--",
                            f"/unibench/bin/debloat/aflasanubsan/{name}"
                        ]
                    elif args.asan:
                        afl_args += [
                            "--",
                            f"/unibench/bin/debloat/aflasan/{name}"
                        ]
                    else:
                        afl_args += [
                            "--",
                            f"/unibench/bin/debloat/aflasan/{name}"
                        ]
                elif args.msan:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflmsan/{name}"
                    ]
                elif args.ubsan:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflubsan/{name}"
                    ]
                elif args.asanubsan:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflasanubsan/{name}"
                    ]
                elif args.asanrecover:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflasan_recover/{name}"
                    ]
                elif args.ubsanrecover:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflubsan_recover/{name}"
                    ]
                elif args.asanrecover:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflasanubsan_recover/{name}"
                    ]
                elif args.msanrecover:
                    afl_args += [
                        "--",
                        f"/unibench/bin/aflmsan_recover/{name}"
                    ]
                else:
                    afl_args += [
                        "--",
                        f"/unibench/bin/justafl/{name}"
                    ]
                

            afl_args += cmds

            all_args = screen_args + docker_args + afl_args
            logging.info(f"args={' '.join(all_args)}")
            subprocess.check_output(all_args)

            next_cpu = ( next_cpu + 1 ) % cpu_count
