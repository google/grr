import {tableSpecs451} from './osquery_raw_table_specs.4.5.1';

/** Osquery column specification, as per schema. */
export interface OsqueryColumnSpec {
  readonly name: string;
  readonly description: string;
  readonly type: string;
  readonly required: boolean;
}

/** Osquery table specification, as per schema. */
export interface OsqueryTableSpec {
  readonly name: string;
  readonly description: string;
  readonly columns: readonly OsqueryColumnSpec[];
  readonly platforms: readonly string[];
}

/** Up-to-date Osquery spec. */
export const allTableSpecs: readonly OsqueryTableSpec[] = tableSpecs451;

/** Returns a table spec corresponding to a given name. */
export function nameToTable(name: string): OsqueryTableSpec | undefined {
  const matches = allTableSpecs.filter((tableSpec) => tableSpec.name === name);
  if (matches.length === 0) {
    return undefined;
  } else if (matches.length === 1) {
    return matches[0];
  } else {
    throw new Error(`More than 1 (${matches.length}) tables have name ${name}`);
  }
}

/** Builds a column spec. */
export function newOsqueryColumnSpec(
  withFields?: Partial<OsqueryColumnSpec>,
): OsqueryColumnSpec {
  return {
    name: 'N/A',
    description: 'N/A',
    type: 'N/A',
    required: false,
    ...withFields,
  };
}

/** Builds a table spec. */
export function newOsqueryTableSpec(
  withFields?: Partial<OsqueryTableSpec>,
): OsqueryTableSpec {
  return {
    name: 'N/A',
    description: 'N/A',
    columns: [],
    platforms: [],
    ...withFields,
  };
}
