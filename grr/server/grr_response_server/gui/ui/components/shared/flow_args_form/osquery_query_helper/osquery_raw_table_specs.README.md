The `osquery_raw_table_specs.*` file holds osquery's table specification as a
single object.

It was generated using a
[script](https://github.com/osquery/osquery/blob/4.5.1/tools/codegen/genwebsitejson.py)
and [osquery table specifications](https://github.com/osquery/osquery/tree/4.5.1/specs),
both taken from the
[open-source osquery repository](https://github.com/osquery/osquery).

High-level instructions for regenerating the file (and updating the
specifications to next osquery versions):
1. Clone the osquery repository
2. Run the script for generating table specifications, pointing it to the
directory with the table specifications. You might need to find a way around
import errors. Save its output to a file.
3. The script produces JSON, but the code requires this data to be in a
typescript `.ts` file. It should suffice to just prefix the output of the script
with something like: `export const tableSpecs451 = ...old json data...`.
4. Update the import statements which use the table specifications inside the
grr codebase. At the moment of writing this, it is only the file
`grr/server/grr_response_server/gui/ui/components/flow_args_form/osquery_query_helper/osquery_table_specs.ts`.
Make sure that the tests run, there are no import errors, and the model of the
data is the same as before (or it is adapted appropriately).
