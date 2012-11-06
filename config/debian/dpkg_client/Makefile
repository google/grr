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
	@mkdir -p $(prefix)/share/grr
	@install -m 0755 dist/grrd/* $(prefix)/share/grr/

.py:

.PHONY: all build clean install

