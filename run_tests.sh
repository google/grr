#!/bin/bash
cd ..
echo 'Running tests...'
PYTHONPATH=. python grr/run_tests.py --processes=1 2>&1|grep -v 'DEBUG:'|grep -v 'INFO:'
