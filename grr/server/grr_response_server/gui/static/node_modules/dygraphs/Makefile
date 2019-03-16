# You should run "npm install" before running any commands in this Makefile.

all: test generate-combined generate-documentation

clean:
	@echo cleaning...
	@cp .dygraph-combined-clean.js dygraph-combined.js
	rm -f docs/options.html

generate-combined:
	@echo Generating dygraph-combined.js
	@./generate-combined.sh

generate-documentation:
	@echo Generating docs/options.html
	@./generate-documentation.py > docs/options.html
	@chmod a+r docs/options.html

gwt: generate-gwt

generate-gwt:
	@echo Generating GWT JAR file
	@./generate-jar.sh

test:
	@./test.sh
	@./check-combined-unaffected.sh

test-combined: move-combined test clean-combined-test

move-combined: generate-combined
	mv dygraph-combined.js dygraph-dev.js

clean-combined-test: clean
	@echo restoring combined
	git checkout dygraph-dev.js
	rm dygraph-combined.js.map

lint:
	@./generate-combined.sh ls \
	    | grep -v 'polyfills' \
	    | xargs ./node_modules/.bin/jshint

# Commands to run for continuous integration on Travis-CI
travis: test test-combined lint

publish:
	./generate-combined.sh
	npm publish
	git checkout dygraph-combined.js
