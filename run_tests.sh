#!/bin/bash

# A convenience script to run all the tests at once

# Make a temp directory
export TEST_TMPDIR=`mktemp -d /tmp/grrtest.XXXXXXXXXX`
export PYTHONPATH="."

python ./grr/lib/access_control_test.py
python ./grr/lib/aff4_test.py
python ./grr/lib/communicator_test.py
python ./grr/lib/fake_data_store_test.py
python ./grr/lib/flow_test.py
python ./grr/lib/flow_utils_test.py
python ./grr/lib/front_end_test.py
python ./grr/lib/lexer_test.py
python ./grr/lib/mongo_data_store_test.py
python ./grr/lib/scheduler_test.py
python ./grr/lib/stats_test.py
python ./grr/lib/test_lib.py
python ./grr/lib/threadpool_test.py
python ./grr/lib/utils_test.py
python ./grr/parsers/chrome_history_test.py
python ./grr/parsers/firefox3_history_test.py
python ./grr/parsers/ie_history_test.py
# Not ready yet
# python ./grr/parsers/linux_log_parser_test.py
python ./grr/parsers/osx_quarantine_test.py
python ./grr/parsers/sqlite_file_test.py
python ./grr/client/client_actions/action_test.py
python ./grr/client/client_actions/file_fingerprint_test.py
python ./grr/client/client_actions/osx/osx_test.py
python ./grr/client/client_test.py
python ./grr/client/client_utils_test.py
python ./grr/client/client_vfs_test.py
python ./grr/worker/worker_test.py
