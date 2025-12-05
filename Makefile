.PHONY: validate-plugin
validate-plugin:
	claude plugin validate ./
	claude plugin validate ./ai-assisted-development/

.PHONY: install-local-marketplace
install-local-marketplace:
	claude plugin marketplace add ./

.PHONY: reinstall-plugin
reinstall-plugin:
	-claude plugin rm ai-assisted-development@claude-code-toolbox
	claude plugin marketplace update claude-code-toolbox
	claude plugin install ai-assisted-development@claude-code-toolbox
