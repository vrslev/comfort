.PHONY: gh
gh:
		open https://github.com/vrslev/comfort

.PHONY: pre
pre:
		pre-commit run --all-files
