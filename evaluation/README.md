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

Please note, a recent kernel introduces changes that [might break ASAN instrumentation](https://github.com/google/sanitizers/issues/1614). This causes issues because the build process of some programs contains bootstraping, e.g. firstly building a helper program and further building other code by the helper program. ASAN instrumentation could crash these helper programs. A quick workaround is: `sudo sysctl vm.mmap_rnd_bits=28`

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

The seeds of UNIFUZZ is available [here](https://github.com/unifuzz/seeds). We use the seeds under `general_evaluation` folder.

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

- Always use tmpfs as output directory, or you get reduced performance.
- Run `afl-fuzz` with `AFL_SAN_ABSTRACTION=simplify_trace`, which is our evaluation setup.

### Start Experiments

TODO