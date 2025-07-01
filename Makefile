SHELL := /bin/bash
VERSION ?= 0.1.1

.PHONY: publish tag release test

packaged.yaml: template.yaml rvm/rvm.py
ifndef ASSETS_BUCKET
	$(error ASSETS_BUCKET is not set)
endif
	aws cloudformation package \
		--template-file template.yaml \
		--s3-bucket $(ASSETS_BUCKET) \
		--output-template-file packaged.yaml

publish: packaged.yaml
ifndef ASSETS_BUCKET
	$(error ASSETS_BUCKET is not set)
endif
	aws s3 cp packaged.yaml s3://$(ASSETS_BUCKET)/rvm-$(VERSION).yaml
	aws s3 cp rvm-workflow-role.yaml s3://$(ASSETS_BUCKET)/rvm-workflow-role-$(VERSION).yaml

tag: test
	git tag -a v$(VERSION) -m "Release $(VERSION)"

release: tag
	git push origin v$(VERSION)

test: rvm/rvm.py tests/test_rvm.py template.yaml rvm-workflow-role.yaml
	pytest
	cfn-lint --ignore-checks W3002 -- template.yaml
	cfn-lint rvm-workflow-role.yaml
	cfn_nag template.yaml rvm-workflow-role.yaml
