#!/bin/bash
#
# Script to delete all data from the mongo database.
#
# This stops all services to release any caches then deletes the database.
#

source "$(dirname $0)/shell_helpers.sh"

stop_services $GRR_SERVICES
echo "Dropping database"
echo "db.dropDatabase()" |  mongo grr
start_services $GRR_SERVICES
