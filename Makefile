PYTHON = python3
PYTEST = pytest
NUCSV_BIN ?= NuSMV

.PHONY: test run-v1 run-v2 verify-v1 verify-bad lint clean

test:
	$(PYTEST) -q

run-v1:
	$(PYTHON) -m src.cli.run examples/v1_straightline/cf_01.tac \
	  --passes const-fold,const-prop,dce \
	  --value-max 7 --max-steps 32 \
	  --emit-opt generated/tac/cf_01.opt.tac \
	  --emit-smv generated/smv/cf_01.smv

run-v2:
	$(PYTHON) -m src.cli.run examples/v2_cfg/branch_fold_01.tac \
	  --passes const-fold,const-prop,branch-fold,unreachable-elim \
	  --value-max 7 --max-steps 32 \
	  --emit-opt generated/tac/branch_fold_01.opt.tac \
	  --emit-smv generated/smv/branch_fold_01.smv

verify-v1:
	$(PYTHON) -m src.cli.run examples/v1_straightline/cf_01.tac \
	  --passes const-fold,const-prop,dce \
	  --value-max 7 --max-steps 32 \
	  --emit-opt generated/tac/cf_01.opt.tac \
	  --emit-smv generated/smv/cf_01.smv --run-nusmv

verify-bad:
	$(PYTHON) -m src.cli.run examples/v1_straightline/bad_div_01.tac \
	  --bad-pass div-self-to-one \
	  --emit-opt generated/tac/bad_div_01.opt.tac \
	  --emit-smv generated/smv/bad_div_01.smv --run-nusmv

lint:
	find src tests -name '*.py' -exec $(PYTHON) -m py_compile {} +

clean:
	rm -f generated/tac/*.tac generated/smv/*.smv generated/logs/*.log
