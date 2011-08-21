#!/bin/bash

# A convenience script to run all the tests at once

# Make a temp directory
export TEST_TMDIR=`mktemp /tmp/grrtest.XXXXXXXXXX`
export PYTHONPATH="."

python ./grr/lib/flow_test.py
python ./grr/lib/test_lib.py
python ./grr/lib/aff4_test.py
python ./grr/lib/scheduler_test.py
python ./grr/lib/front_end_test.py
python ./grr/lib/communicator_test.py
python ./grr/lib/mongo_data_store_test.py
python ./grr/lib/utils_test.py
python ./grr/parsers/chrome_history_test.py
python ./grr/client/client_actions/file_fingerprint_test.py
python ./grr/client/client_actions/action_test.py
python ./grr/client/client_test.py
python ./grr/client/client_vfs_test.py
python ./grr/worker/worker_test.py
