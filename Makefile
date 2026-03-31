.PHONY: validate-plugin
validate-plugin:
	claude plugin validate ./
	claude plugin validate ./ai-assisted-development/

.PHONY: install-local-marketplace
install-local-marketplace:
	@output=$$(claude plugin marketplace add ./ 2>&1) || { \
		if echo "$$output" | grep -q "Marketplace '.*' is already installed"; then \
			echo "Marketplace already installed, updating..."; \
			claude plugin marketplace update claude-code-toolbox; \
		else \
			echo "$$output" >&2; \
			exit 1; \
		fi; \
	}

.PHONY: install-plugin
install-plugin: install-local-marketplace
	-claude plugin rm ai-assisted-development@claude-code-toolbox
	claude plugin marketplace update claude-code-toolbox
	claude plugin install ai-assisted-development@claude-code-toolbox

.PHONY: test
test:
	python -m unittest discover -s ai-assisted-development/tests -p "test_*.py" -v
