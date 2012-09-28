# This generates HTML documentation from the txt files in this directory. You
# will need to have asciidoc installed first (apt-get install asciidoc). Then
# type make in this directory.

# All html files depend on their respective txt files.
html_files := $(patsubst %.txt,%.html,$(wildcard *.txt))

# Make all html files from any txt files found here.
all: $(html_files)

%.html: %.txt
	asciidoc -a icons $(<F)

.PHONY: clean
clean:
	rm *.html