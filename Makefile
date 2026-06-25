# DeepInit — there is no application code here; the "build" is validation.
# `make validate` runs every gate (harness + stats drift + count drift + mutation + public-harness).
# Portable entry point regardless of make: `python tools/validate_all.py`.

PYTHON ?= python
export PYTHONUTF8 = 1

.PHONY: validate validate-fast harness mutation stats drift public-harness golden report-preview report-smoke

validate: ## Run every validation gate (the full surface)
	$(PYTHON) tools/validate_all.py

validate-fast: ## Run gates 1-4 (skip the public-harness re-run)
	$(PYTHON) tools/validate_all.py --fast

harness: ## Just the deterministic harness
	$(PYTHON) tests-fixtures-v1/_chat_validation.py

mutation: ## Just the mutation meta-harness
	$(PYTHON) tests-fixtures-v1/_mutation_harness.py

stats: ## Regenerate STATS.json from the records
	$(PYTHON) tools/build_stats.py

drift: ## Check page/README figures match STATS.json
	$(PYTHON) tools/check_stats_drift.py

public-harness: ## Prove the suite is green without the internal held-out keys
	$(PYTHON) tools/public_harness.py

golden: ## Regenerate the canonical e2e golden snapshot (deliberate)
	$(PYTHON) tools/build_golden_snapshot.py validation/end-to-end/kemal --write

report-preview: ## Build the report against a fixture WITH a populated graph + docs (open it to eyeball the Map view)
	$(PYTHON) tools/build_report.py validation/end-to-end/kemal
	@echo "open validation/end-to-end/kemal/.ai/report.html in a browser — click the Map tab (pan/zoom, click a node -> its docs)"

report-smoke: ## Headless jsdom render test of the report (Docs/Insights/Map + node-navigation + honest-degrade)
	$(PYTHON) tools/build_report.py validation/end-to-end/kemal
	node tools/smoke_report.mjs validation/end-to-end/kemal/.ai/report.html
