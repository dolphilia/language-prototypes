SHELL := /bin/bash
ROOT := $(abspath .)
CC := xcrun clang
PYTHON := python3
.DEFAULT_GOAL := verify

.PHONY: p0 p0-native p0-proof

build:
	mkdir -p build

build/probe_ret.o: tests/probe_ret.S | build
	$(CC) -arch arm64 -c $< -o $@

build/probe_ret: tests/probe_ret.c build/probe_ret.o
	$(CC) -arch arm64 -O2 -Wall -Wextra -Werror $^ -o $@

p0-native: build/probe_ret
	$(PYTHON) tools/check_artifacts.py --probe
	build/probe_ret
	$(PYTHON) -m unittest discover -s tests -p 'test_artifacts.py'

.deps/s2n-bignum/arm/generic/word_max.o:
	$(MAKE) -C .deps/s2n-bignum/arm generic/word_max.o

p0-proof: build/probe_ret.o .deps/s2n-bignum/arm/generic/word_max.o
	$(PYTHON) tools/run_proof.py --probe

p0-driver:
	$(PYTHON) -m unittest discover -s tests -p 'test_proof_driver.py'

p0: p0-native p0-proof p0-driver

build/generate: generator/main.ml | build
	ocamlc -c -o build/generator.cmo $<
	ocamlc -o $@ build/generator.cmo

build/macros.stamp: build/generate
	build/generate build
	touch $@

build/vp_macro_%.o: build/macros.stamp
	$(CC) -arch arm64 -c build/vp_macro_$*.S -o $@

p1-objects: build/vp_macro_copybyte.o build/vp_macro_fillbyte.o build/vp_macro_copy8.o build/vp_macro_copybyte_indexed.o build/vp_macro_fillbyte_indexed.o

build/vp_memcpy_scalar.o build/vp_memset.o build/vp_memcpy.o: build/macros.stamp
	$(CC) -arch arm64 -c $(@:.o=.S) -o $@

p2-objects: build/vp_memcpy_scalar.o build/vp_memset.o

build/abi.o: tests/abi.S | build
	$(CC) -arch arm64 -c $< -o $@

build/test_memory: tests/memory.c include/vp_memory.h build/abi.o build/vp_memcpy_scalar.o build/vp_memcpy.o build/vp_memset.o
	$(CC) -arch arm64 -O2 -Wall -Wextra -Werror -fno-builtin -fno-lto -Iinclude tests/memory.c build/abi.o build/vp_memcpy_scalar.o build/vp_memcpy.o build/vp_memset.o -o $@

native: build/test_memory
	build/test_memory

build/benchmark: benchmarks/memory.c include/vp_memory.h build/vp_memcpy_scalar.o build/vp_memcpy.o build/vp_memset.o
	$(CC) -arch arm64 -O2 -Wall -Wextra -Werror -fno-builtin -fno-lto -Iinclude benchmarks/memory.c build/vp_memcpy_scalar.o build/vp_memcpy.o build/vp_memset.o -o $@

build/scalar/vp_memcpy.o: build/generate
	mkdir -p build/scalar
	build/generate build/scalar baseline-public
	$(CC) -arch arm64 -c build/scalar/vp_memcpy.S -o $@

build/size_scalar: benchmarks/size.c include/vp_memory.h build/scalar/vp_memcpy.o build/vp_memset.o
	$(CC) -arch arm64 -O2 -Wall -Wextra -Werror -fno-builtin -fno-lto -Iinclude benchmarks/size.c build/scalar/vp_memcpy.o build/vp_memset.o -o $@

build/size_optimized: benchmarks/size.c include/vp_memory.h build/vp_memcpy.o build/vp_memset.o
	$(CC) -arch arm64 -O2 -Wall -Wextra -Werror -fno-builtin -fno-lto -Iinclude benchmarks/size.c build/vp_memcpy.o build/vp_memset.o -o $@

bench-build: build/benchmark build/size_scalar build/size_optimized

.PHONY: verify measure native p0-driver p1-objects p2-objects bench-build
verify:
	$(PYTHON) tools/verify.py

measure: verify
	$(PYTHON) tools/measure.py
