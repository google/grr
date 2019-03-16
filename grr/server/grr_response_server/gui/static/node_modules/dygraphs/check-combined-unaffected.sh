#!/bin/bash
# Ensures that dygraph-combined.js is unaffected.
# Helpful for pull requests, where this is a common mistake.

grep 'var' dygraph-combined.js > /dev/null
if [ $? -eq 0 ]; then
  echo 'Please revert changes to dygraph-combined.js' >&2
  echo 'You can do this by running:  ' >& 2
  echo '' >& 2
  echo '    git checkout dygraph-combined.js' >&2
  echo '' >& 2
  exit 1
fi

exit 0
