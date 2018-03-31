#!/bin/bash

counter=2
echo '// The following messages are used to start OSQuery flows in GRR.'
echo ''
echo 'syntax = "proto2";'
echo ''
echo 'import "grr_response_proto/semantic.proto";'
echo ''
echo 'message OSQueryRunQueryArgs {'
echo '  optional string query = 1 [(sem_type) = {'
echo '      description: "OSQuery SQL statement; passed as a string."'
echo '    }];'
echo '}'
echo ''
echo ''
echo 'message OSQueryRunQueryResult {'
echo '  optional string error_msg = 1;'
osqueryi ".schema" | grep -o -P '(?<=\().*(?=\))' | tr ',' '\n' | grep -v 'PRIMARY' | grep -v ')' | grep -o -P '(?<=`).*(?=`)' | sort -u | while read -r column; do
echo "  repeated string ${column} = ${counter};";
counter=$((counter+1))
done
echo '}'