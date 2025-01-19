# SAND

This repo will contain the implementation and paper for "SAND: Decoupling Sanitization from Fuzzing for Low Overhead".

Preprint is available [here](./paper.pdf) and we will have camera-reday version uploaded shortly.

The original AFL++ README is available [here](./README.AFLpp.md).

## Branch organization

- sand: Forked from 4.05c, this branch contains the version used in our paper evaluation. Please use this for any evaluation against SAND.
- upstream: Forked from AFLplusplus mainstream, this branch contains our efforts to port SAND to the latest AFLplusplus.

## Basic Usage

To use SAND, two binaries need to be built like cmplog:

- The native binary without any sanitizer instrumented. SAND will run it during every loop and collect coverage. 
- The sanitizer instrumented binary but _without AFL instrumentation_. SAND use this binary to check if an interesting input triggers sanitizers.

### Build

Docker is highly recommened to reproduce the build. Simply do:

```
docker build -t sand .
```

If docker is not available, follow [The original AFL++ README](./README.AFLpp.md) to build SAND.

Note we further provide `Dockerfile.ASAN--` and `Dockerfile.UNIFUZZ` for evaluation reproduction.

### Simple Example

The following steps assume you have built the docker image and started a container. If not, do it with:

```
docker run --rm -it sand
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

That's it!

## Evaluation Reproduction

TODO

## Cite

```bib
@inproceedings{sand,
    author = {Ziqiao Kong, Shaohua Li, Heqing Huang, Zhendong Su},
    title = {SAND: Decoupling Sanitization from Fuzzing for LowOverhead},
    booktitle = {IEEE/ACM International Conference on Software Engineering (ICSE)},
    year = {2025},
}
```