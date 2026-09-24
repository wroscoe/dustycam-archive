#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
build_dir="${TMPDIR:-/tmp}/xiao_pantilt_pt_core_tests"
mkdir -p "$build_dir"
gcc -std=c11 -Wall -Wextra -Werror -pedantic -I main main/pt_core.c tests/test_pt_core.c -lm -o "$build_dir/test_pt_core"
"$build_dir/test_pt_core"
