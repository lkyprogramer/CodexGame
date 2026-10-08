#!/bin/sh
# Exit 0 when a Strata tree already has the CUDA 12.3 / ModelScope behavior
# this host used to carry as a local diff. Exit 1 when a future upgrade
# dropped it and the old diff must NOT be replayed blindly: patch the
# missing site from docs/strata-patches/README.md.
set -eu
root=${1:-/home/hhtele/strata}
fail=0

need() {
  file=$1
  pattern=$2
  why=$3
  if grep -q "$pattern" "$root/$file"; then
    echo "ok  $file  $why"
  else
    echo "MISSING  $file  $why" >&2
    fail=1
  fi
}

need src/core/vmm.cpp 'CUDART_VERSION >= 12050' 'CUDA 12.5 gate'
need src/core/vmm.cpp 'cudaGetDriverEntryPoint(' 'CUDA 12.2-12.4 fallback'
need include/strata/core/vmm.hpp 'std::size_t' 'size_t cast'
need tools/mtp_fetch.py 'STRATA_SOURCE' 'ModelScope keeps SHA256 checks'

if [ "$fail" -ne 0 ]; then
  echo "upstream fallback is incomplete; see docs/strata-patches/README.md" >&2
  exit 1
fi
echo "cuda 12.3 fallback and modelscope pin are in tree"
