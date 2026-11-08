SHELL := /bin/bash
PYTHON := python3
.DEFAULT_GOAL := verify-all

.PHONY: build check-e0 check-composition native
build:
	$(PYTHON) tools/build.py
check-e0: build
	$(PYTHON) tools/verify_e0.py
check-composition: build
	$(PYTHON) tools/verify_composition.py
native: build
	$(PYTHON) tools/native.py

.PHONY: verify-m1 verify-m2 verify-m3 verify-all measure-m1 measure-m2 measure-m3 proof-costs audit-m1

verify-m1:
	$(PYTHON) tools/verify_m1.py
proof-costs: build
	$(PYTHON) tools/verify_costs.py
measure-m1:
	$(PYTHON) tools/measure_m1.py
audit-m1:
	$(PYTHON) tools/audit_m1.py

# Each phase is implemented as its evidence becomes available. Missing phases
# deliberately fail; there are no empty success targets.
verify-m2 verify-m3 verify-all measure-m2 measure-m3:
	$(PYTHON) tools/entry.py $@

.PHONY: audit-m2 audit-m3 audit-all
audit-m2:
	$(PYTHON) tools/audit_m2.py
audit-m3:
	$(PYTHON) tools/audit_m3.py
audit-all:
	$(PYTHON) tools/audit_all.py
