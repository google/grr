# This generates HTML documentation from the txt files in this directory. You
# will need to have asciidoc installed first (apt-get install asciidoc). Then
# type make in this directory.

# All html files depend on their respective txt files.
html_files := $(patsubst DONT_EDIT_%.adoc,%.html,$(wildcard *.adoc))

adoc_files := $(wildcard *.adoc)

TEMPDIR := $(shell mktemp -d)

# Make all html files from any txt files found here.
all: $(html_files)

sync:
	git clone https://github.com/google/grr-doc.git $(TEMPDIR)

	for adoc_file in $(patsubst DONT_EDIT_%.adoc,%.adoc, $(adoc_files)); \
	do \
	cp $(TEMPDIR)/$$adoc_file ./DONT_EDIT_$$adoc_file; \
	done

	rm -rf $(TEMPDIR)

%.html: DONT_EDIT_%.adoc
	asciidoc -a icons -o $(@F) $(<F)
	sed -ri 's/\"(.*).adoc/\"\1\.html/' $(@F)

.PHONY: sync clean
clean:
	rm *.html
