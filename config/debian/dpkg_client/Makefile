# GRR Rapid Response Client Makefile

# PYINSTALLER=/usr/local/bin/pyinstaller.py
PYINSTALLER=../pyinstaller/pyinstaller.py

BUILDFILES=grr/client/client.py
BUILDNAME=grrd

prefix=debian/tmp/usr

all: build

build: $(BUILDFILES)
	$(PYINSTALLER) \
	  --onedir \
	  --console \
	  --strip \
	  --name=$(BUILDNAME) \
	  $<

clean:
	@rm -rf build/ dist/

install:
	@mkdir -p $(prefix)/lib/grr
	@install -m 0755 dist/grrd/*.* $(prefix)/lib/grr/
	@install -m 0755 dist/grrd/grrd $(prefix)/lib/grr/

.py:

.PHONY: all build clean install

