PYTHON ?= .venv/bin/python
RUN_DIR ?= results/reproduced
SUPPORT_DIR ?= $(RUN_DIR)/support
CHECK_DIR ?= results/verification
FIG_DIR ?= results/displays
FOLLOWUP_DIR ?= results/followup-checks
export PYTHONPATH := src
export PYTHONDONTWRITEBYTECODE := 1
export MPLCONFIGDIR := $(CURDIR)/.cache/matplotlib

.PHONY: setup test verify analyses displays fetch-data verify-data prepare-inputs prepare smoke reproduce
setup:
	uv sync --frozen
test:
	$(PYTHON) -W error -m unittest discover -s tests -p 'test_*.py' -v
verify:
	$(PYTHON) experiments/joint_queries/verify_current.py --primary $(RUN_DIR) --support $(SUPPORT_DIR) --output $(CHECK_DIR)
analyses:
	$(PYTHON) experiments/joint_queries/analyse_followups.py --primary $(RUN_DIR) --support $(SUPPORT_DIR) --output $(FOLLOWUP_DIR)
displays:
	$(PYTHON) experiments/joint_queries/render_current.py --output $(FIG_DIR)
fetch-data:
	$(PYTHON) experiments/joint_queries/acquire_inputs.py fetch
verify-data:
	$(PYTHON) experiments/joint_queries/acquire_inputs.py verify
prepare-inputs:
	$(PYTHON) experiments/joint_queries/prepare_inputs.py
prepare:
	$(PYTHON) experiments/joint_queries/run_queries.py prepare --output $(RUN_DIR)
smoke:
	$(PYTHON) experiments/joint_queries/smoke_provider.py --output $(RUN_DIR)-smoke
reproduce: prepare
	$(PYTHON) experiments/joint_queries/run_queries.py run --output $(RUN_DIR)
	$(PYTHON) experiments/joint_queries/run_queries.py check --output $(RUN_DIR)
	$(PYTHON) experiments/joint_queries/run_queries.py summarise --output $(RUN_DIR)
	$(PYTHON) experiments/joint_queries/run_support.py prepare --source $(RUN_DIR) --output $(SUPPORT_DIR)
	$(PYTHON) experiments/joint_queries/run_support.py run --source $(RUN_DIR) --output $(SUPPORT_DIR)
	$(PYTHON) experiments/joint_queries/run_support.py check --source $(RUN_DIR) --output $(SUPPORT_DIR)
	$(PYTHON) experiments/joint_queries/analyse_followups.py --primary $(RUN_DIR) --support $(SUPPORT_DIR) --output $(RUN_DIR)/followups
	$(PYTHON) experiments/joint_queries/compare_current.py --primary $(RUN_DIR) --support $(SUPPORT_DIR)
