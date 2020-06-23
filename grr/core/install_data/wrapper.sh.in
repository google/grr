#!/bin/bash

# Workaround for:
# https://github.com/pyinstaller/pyinstaller/issues/4674
# We can't execute grrd from a symlink, we have to create a wrapper script.

exec "%(ClientBuilder.target_dir)/%(Client.binary_name)" "$@"
