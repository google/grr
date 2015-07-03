#!/bin/bash
cd ..
echo 'Running tests...'

EXCLUDE_TESTS=\
HTTPDataStoreCSVBenchmarks,\
HTTPDataStoreBenchmarks,\
MicroBenchmarks,\
FakeDataStoreBenchmarks,\
AverageMicroBenchmarks,\
SqliteDataStoreBenchmarks,\
DataStoreCSVBenchmarks,\
AFF4Benchmark
PYTHONPATH=. \
python grr/run_tests.py \
  --processes=1 \
  --exclude_tests=$EXCLUDE_TESTS
exit $?
