#!/bin/bash
#
# Script to delete all data from the mongo database.
#
# This stops all services to release any caches then deletes the database.
#

SERVICES="grr-single-server grr-http-server grr-ui grr-enroller grr-worker"

for SVC in $SERVICES
do
  service $SVC stop;
done

echo "Dropping database"
echo "db.dropDatabase()" |  mongo grr

for SVC in $SERVICES
do
  service $SVC start;
done
