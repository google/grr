#!/bin/bash
# Script to prepare the GRR protobufs and database on Spanner

echo "1/3 : Bundling GRR protos in spanner_grr.pb..."
if [ ! -f ./spanner_grr.pb ]; then
  protoc -I=../../../proto -I=/usr/include --include_imports --descriptor_set_out=./spanner_grr.pb \
    ../../../proto/grr_response_proto/analysis.proto \
    ../../../proto/grr_response_proto/artifact.proto \
    ../../../proto/grr_response_proto/flows.proto \
    ../../../proto/grr_response_proto/hunts.proto \
    ../../../proto/grr_response_proto/jobs.proto \
    ../../../proto/grr_response_proto/knowledge_base.proto \
    ../../../proto/grr_response_proto/objects.proto \
    ../../../proto/grr_response_proto/output_plugin.proto \
    ../../../proto/grr_response_proto/signed_commands.proto \
    ../../../proto/grr_response_proto/sysinfo.proto \
    ../../../proto/grr_response_proto/user.proto  \
    ../../../proto/grr_response_proto/rrg.proto \
    ../../../proto/grr_response_proto/rrg/fs.proto \
    ../../../proto/grr_response_proto/rrg/startup.proto \
    ../../../proto/grr_response_proto/rrg/action/execute_signed_command.proto
fi

echo "2/3 : Creating GRR database on Spanner..."
gcloud spanner databases create ${SPANNER_DATABASE} --instance ${SPANNER_INSTANCE}

echo "3/3 : Creating tables ..."
gcloud spanner databases ddl update ${SPANNER_DATABASE} --instance=${SPANNER_INSTANCE} --ddl-file=spanner.sdl --proto-descriptors-file=spanner_grr.pb