#!/bin/bash
cd ..
echo 'Running tests...'

EXCLUDE_TESTS=\
HTTPDataStoreCSVBenchmarks,\
HTTPDataStoreBenchmarks,\
MicroBenchmarks,\
TDBDataStoreBenchmarks,\
FakeDataStoreBenchmarks,\
AverageMicroBenchmarks,\
SqliteDataStoreBenchmarks,\
DataStoreCSVBenchmarks,\
TDBDataStoreCSVBenchmarks,\
AFF4Benchmark
PYTHONPATH=. \
python grr/run_tests.py \
  --processes=1 \
  --exclude_tests=$EXCLUDE_TESTS 2>&1\
  |grep -v 'DEBUG:'\
  |grep -v 'INFO:'
TEST_STATUS=${PIPESTATUS[0]}
exit $TEST_STATUS
