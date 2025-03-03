# Evaluation Reproduction

## Build images

Building the evaluation images might take ~10-30 hours depending on your CPU and memory configuration. **To facilitate reproduction, we provide prebuilt docker images for all steps**:

- [lazymio/sand](https://hub.docker.com/r/lazymio/sand): Base image of SAND
- [lazymio/debloat12](https://hub.docker.com/r/lazymio/debloat12): Base image of debloat12 (ASAN--)
- [lazymio/sand-unifuzz](https://hub.docker.com/r/lazymio/sand-unifuzz): The image used to evaluate SAND against UNIFUZZ
- [lazymio/sand-debloat12](https://hub.docker.com/r/lazymio/sand-debloat12): The image used to evaluate debloat12 against UNIFUZZ

Some building process might has a dependency on the host kernel version and our evaluation environment is:

```bash
> uname -a
Linux <redacted> 5.4.0-200-generic #220-Ubuntu SMP Fri Sep 27 13:19:16 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
> cat /etc/issue
<redacted> Ubuntu 20.04 (x86_64)
```

Please note, a recent kernel introduces changes that [might break ASAN instrumentation](https://github.com/google/sanitizers/issues/1614). This causes issues because the build process of some programs contains bootstraping, e.g. firstly building a helper program and further building other code by the helper program. ASAN instrumentation could crash these helper programs. A quick workaround is: `sudo sysctl vm.mmap_rnd_bits=28` for newer kernels but we recommend sticking to kernel `5.4.0-200-generic` for serious evaluations.

When building docker images, you should do it under the repo root directory instead of this subdirectory.

### Build UNIFUZZ Image

For easy experiment, we bundle all targets within the SAND image. Build it via:

```bash
docker build -t sand-unifuzz -f Dockerfile.UNIFUZZ .
```

To save time, we upload a public reproduction docker image:

```bash
docker pull lazymio/sand-unifuzz
```

The seeds of UNIFUZZ is available [here](https://github.com/unifuzz/seeds) or `/unibench/seeds`. We use the seeds under `general_evaluation` folder.

### ASAN-- baseline

Firstly, build ASAN-- with:

```bash
git clone https://github.com/wtdcode/ASAN-- debloat12
cd debloat12 && docker build -t debloat12 -f Dockerfile_ASAN-- .
```

Likewise, build another all-in-one image for the base line:

```bash
docker build -t sand-debloat12 -f Dockerfile.ASAN-- .
```

Again, we upload prebuilt image:

```bash
docker pull lazymio/debloat12 # optional
docker tag lazymio/debloat12 debloat12 # optional
docker pull lazymio/sand-debloat12
```

### Merge Image

For ease of experiment, it is possible to merge the two images to a single image. We provide a script [merge.sh](./merge.sh) to do so:

```bash
./merge.sh sand-debloat12 sand-unifuzz
```

This will produce an image `sand-debloat12-sand-unifuzz-merged`.

In addition, it is painful to rebuild all UNIFUZZ and Debloat targets every time you make a few modifications. [update-unifuzz.sh](./update-unifuzz.sh) is designed to only update SAND and copy targets from existing images. 

```bash
./update-unifuzz.sh sand-debloat12-sand-unifuzz-merged sand
```

This builds an image named `sand-from-sand-debloat12-sand-unifuzz-merged` from current directory and copies targets from `sand-debloat12-sand-unifuzz-merged`

## Preparation

Before really starting experiments, a few things to note:

- Always use tmpfs as output directory, or you get greatly reduced performance.
- Run `afl-fuzz` with `AFL_SAN_ABSTRACTION=simplify_trace`, which is our evaluation setup. This has been enforced in all our default evaluation setups like the `eval.py` detailed in the next section. Unless you are exploring alternative abstractions (execution patterns) or manually starting `afl-fuzz`, you do not need to care about this.

### Start Experiments

In most cases, you don't need to really start containers by yourself. [eval.py](./eval.py) is the core script to start fuzzing campaigns so that you can control the compagins on the host machine instead of executing commands in containers manually.

```bash
usage: eval [-h] --image IMAGE [--msan] [--asan] [--ubsan] [--asanubsan] [--asanubsanrecover] [--ubsanrecover] [--asanrecover] [--msanrecover] [--debloat] [--single] [--seconds SECONDS] --seeds SEEDS [--repeat REPEAT]
            [--output OUTPUT] [--timeout TIMEOUT] [--schedule SCHEDULE] [--rng RNG] [--cpu CPU] [-D] [-d] [--gdb] [--valgrind] [--abstraction ABSTRACTION]
            programs [programs ...]

positional arguments:
  programs              Programs: exiv2,tiffsplit,mp3gain,wav2swf,pdftotext,infotocap,mp42aac,flvmeta,objdump,tcpdump,ffmpeg,gdk-pixbuf-pixdata,cflow,nm,sqlite3,lame,jhead,imginfo,jq,mujs

options:
  -h, --help            show this help message and exit
  --image IMAGE         Docker image name
  --msan                MSAN binary
  --asan                ASAN binary
  --ubsan               UBSAN binary
  --asanubsan           ASAN+UBSAN binary
  --asanubsanrecover    UBSAN binary but skipp all errors
  --ubsanrecover        UBSAN binary but skipp all errors
  --asanrecover         ASAN binary but skipp all errors
  --msanrecover         MSAN binary but skipp all errors
  --debloat             Eval debloat
  --single              Eval single sanitizer
  --seconds SECONDS     Fuzzing time limit.
  --seeds SEEDS         Path to the seeds
  --repeat REPEAT       Repeat
  --output OUTPUT       Output folder
  --timeout TIMEOUT     Timeout
  --schedule SCHEDULE   AFL schedule
  --rng RNG             rng seeds
  --cpu CPU             Start of CPU
  -D                    AFL -D
  -d                    AFL -d
  --gdb                 Starts with gdb
  --valgrind            Starts with valgrind
  --abstraction ABSTRACTION
                        abstraction to use
```

Although there are bunch of arguments, only a few of them are essential:

- `image`: The image to be used. You can use the images built above. Personally recommend merging images before starting experiments.
- `msan/asan/asanubsan/debloat`: As suggested, this options will start fuzzing campaigns with these sanitizers.
- `single`: If this option is given, we are running the single sanitizers instead of SAND, i.e. vanilla fuzzing workflows baselines in our paper. If this option is not given, SAND is used instead.
- `seconds`: The duration of the fuzzing campaigns, 86400 in our paper.
- `seeds`: The path to the seeds (outside docker containers on the host machine!).
- `output`: The path to the output (outside docker containers on the host machine!), and should be tmpfs. The directory will be created if not existing.
- `repeat`: How many times to repeat for each fuzzing campaigns, 20 in our paper.
- `cpu`: The starting cpu to bind. For example, if you request 20 repeats and cpu is starting from 0, `eval.py` will spawn docker containers binding to cpu 0, 1, 2...19 for the first benchmark, 20, 21...39 for the next until all cores are occupied.
- `abstraction`: Default to `simplify_trace` as suggested above. This will pass in `AFL_SAN_ABSTRACTION=simplify_trace`. Alternatively, you could use `unique_trace` or `coverage_increase`, both of which are alternative execution patterns mentioned in our paper.

For example, some common usages:

- Start all experiments as our paper evaluation setup (simplified trace, 20 repeats, 24 hours, all sanitizers etc)

```bash
python3 eval.py --image sand-unifuzz --asanubsan --msan --seeds /path/to/seeds/general_evaluation \ 
                --repeat 20 --output /path/to/tmpfs/unifuzz --timeout 86400 -D \ 
                all
```

- Start all experiments but with an alternative execution pattern.

```bash
# unique_trace could catch almost all bug-triggering inputs but have much lower throughput.
# coverage_increase misses more than 20% bugs but is faster.
python3 eval.py --image sand-unifuzz --asanubsan --msan --seeds /path/to/seeds/general_evaluation \ 
                --abstraction unique_trace --repeat 20 --output /path/to/tmpfs/unifuzz --timeout 86400 -D \ 
                all
```

- Start one program for only asanubsan and only 1 repeat (useful for debugging purpose)

```bash
python3 eval.py --image sand-unifuzz --asanubsan --single --seeds /path/to/seeds/general_evaluation \ 
                --repeat 1 --output /path/to/tmpfs/asanubsan --timeout 86400 -D \ 
                imginfo
```

- Start native vanilla AFL++ withtout sanitizers

```bash
python3 eval.py --image sand-unifuzz --single --seeds /path/to/seeds/general_evaluation \ 
                --repeat 20 --output /path/to/tmpfs/native --timeout 86400 -D \ 
                all
```

### Colllect Results

After the fuzzing campaigns reach timeout, you will find all results under the given output directory above. Each campaign will have a standalone folder.

The very first step is to deduplicate all crashes. We used [afl-btmin](https://github.com/wtdcode/afl-btmin) to do so.

First, start another container. Assume the previous results are located at `/path/to/tmpfs/unifuzz`, you should do:

```bash
docker run --rm -it -v /path/to/tmpfs/unifuzz:/work lazymio/sand-unifuzz bash
```

**Note: The image used here should be consistent with the fuzzing campaigns!**

Then, install the afl-btmin:

```bash
cd /
git clone https://github.com/wtdcode/afl-btmin
echo "source /afl-btmin/afl-btmin-gdb.py" >> ~/.gdbinit
echo "export PATH=$PATH:/afl-btmin" >> ~/.bashrc
source ~/.bashrc
```

To verify the installation, simply do:

```bash
cd / && afl-btmin.py --help
```

This should give you the help usage of `afl-btmin`.

We provide another script [mini.py](./mini.py) to help you automate the process. Simply run:

```bash
cd /AFLplusplus/evaluation
python3 mini.py --output /work
```

Unfortunately, this process can take _very long_ because not all crashes can be reproduced after fuzzing campaigns or some crashes might have infinite loop/recursion and we run each crash a few times to collect the precise backtraces. In worst cases, we took ~12 hours to minimize all crashes for our evaluation setup. Do note that [mini.py](./mini.py) already utilizes multithread to speed up.

In addition, as suggested above, we observed that some programs' behavior will change per different kernel versions. Therefore, you might adjust the script accordingly, we have put a few heuristic rules in the script, though.

This shall deduplicate >90% crashes in our experiment, on some targets, even all crashes. For the last 10% crashes, unfortunately we have to go through a manual process. Generally, we did this following practice from [Magma](https://hexhive.epfl.ch/publications/files/21SIGMETRICS.pdf): Find bug reports/fix from upstream, identify the root cause and manually merge the crashes. For example, a common bug is lacking checks for the length of some fields but causing crashes in different locations.

After the deduplication is done, we have a script [data.py](./data.py) to collect these data. Most tables and figures are made from these raw results. We recommend running the script inside the same container.

Usage:

```bash
python3 data.py --output /path/to/tmpfs/output
```

Note this also collects throughput and a few other metrics.