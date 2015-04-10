# This script pulls artifacts from the ForensicsAritfacts repository. All
# existing artifacts are deleted in the process. Local (non-public) artifacts
# should live in the local/ subdirectory and will remain untouched.

TEMPDIR := $(shell mktemp -d artifact.XXXXXX)

all: sync

sync:
	git clone https://github.com/ForensicArtifacts/artifacts.git $(TEMPDIR)
	-rm -f *.yaml

	cp $(TEMPDIR)/definitions/*.yaml .

	rm -rf $(TEMPDIR)

.PHONY: sync clean

clean:
	-rm -f *.yaml
