# SAND

This repo will contain the implementation and paper for "SAND: Decoupling Sanitization from Fuzzing for Low Overhead".

Preprint is available [here](./paper.pdf) and we will have camera-reday version uploaded shortly.

The original AFL++ README is available [here](./README.AFLpp.md).

## Branch organization

- [sand](https://github.com/wtdcode/sand-aflpp/tree/sand): Forked from 4.05c, this branch contains the reference implementation used in our paper evaluation. Please use this for any evaluation against SAND.
- [upstream](https://github.com/wtdcode/sand-aflpp/tree/upstream): Forked from AFLplusplus mainstream, this branch contains our efforts to port SAND to the latest AFLplusplus.

Track the upstream progress [here](https://github.com/AFLplusplus/AFLplusplus/pull/2288).

## Basic Usage

To use SAND, two binaries need to be built like cmplog:

- The native binary without any sanitizer instrumented. SAND will run it during every loop and collect coverage. 
- The sanitizer instrumented binary but _without AFL instrumentation_. SAND use this binary to check if an interesting input triggers sanitizers. Note, this binary must have fork servers enabled so `afl-clang-fast` is still needed for compilation. We will explain how to build this below.

### Build

Docker is highly recommened to reproduce the build. Simply do:

```bash
docker build -t sand .
# alternatively
# docker pull lazymio/sand
```

If docker is not available, follow [The original AFL++ README](./README.AFLpp.md) to build SAND.

### Simple Example

The following steps assume you have built the docker image and started a container. If not, do it with:

```bash
docker run --rm -it sand
# alternatively
# docker run --rm -it lazymio/sand
```

Take `test_instr.c` as an example, firstly build the native binary:

```
afl-clang-fast test-instr.c -o ./native
```

Then build the sanitizer instrumented binary but without AFL instrumentation:

```
AFL_SAN_NO_INST=1 AFL_USE_ASAN=1 afl-clang-fast test-instr.c -o ./san
```

Run SAND:

```
mkdir /tmp/test
echo "a" > /tmp/test/a
# Note the "-a ./san" parameter.  
AFL_NO_UI=1 AFL_SKIP_CPUFREQ=1 afl-fuzz -i /tmp/test -o /tmp/out -a ./san -- ./native -f @@
```

That's it! We also have detailed usage and caveats [here](./docs/SAND.md).

## Evaluation Reproduction

See [evaluation](./evaluation/) folder for detailed instructions.

## Other AFLplusplus Schedule

We use the default schedule of AFLplusplus but other schedule should be agnostic to our approach. We also evaluated SAND on the `mmopt` schedule of AFLplusplus and confirmed the similar performance.

## Port SAND to other fuzzers

The approach of SAND is rather simple and easy to port to other fuzzers. We once applied SAND on [Fuzzilli](https://github.com/wtdcode/sand_fuzzilli). Due to time and pages limitation, we didn't spend too much time exploring this direction.

## Cite

```bib
@inproceedings{sand,
    author = {Ziqiao Kong and Shaohua Li and Heqing Huang and Zhendong Su},
    title = {SAND: Decoupling Sanitization from Fuzzing for LowOverhead},
    booktitle = {IEEE/ACM International Conference on Software Engineering (ICSE)},
    year = {2025},
}
```
