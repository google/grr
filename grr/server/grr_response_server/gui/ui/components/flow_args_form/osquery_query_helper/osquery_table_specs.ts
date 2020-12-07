import tablesJson from '../../../../static/osquery_table_specs_4_5_1.json';

export interface OsqueryColumnSpec {
  readonly name: string;
  readonly description: string;
  readonly type: string;
  readonly required: boolean;
}

export interface OsqueryTableSpec {
  readonly name: string;
  readonly description: string;
  readonly columns: ReadonlyArray<OsqueryColumnSpec>;
  readonly platforms: ReadonlyArray<string>;
}

export const allTableSpecs: ReadonlyArray<OsqueryTableSpec> = tablesJson;

export function nameToTable(name: string) {
  const matches = allTableSpecs.filter(tableSpec => tableSpec.name === name);
  if (matches.length === 0) {
    return null;
  } else if (matches.length === 1) {
    return matches[0];
  } else {
    throw Error(`More than 1 (${matches.length}) tables have name ${name}`);
  }
}

export function newOsqueryColumnSpec(
    withFields?: Partial<OsqueryColumnSpec>,
): OsqueryColumnSpec {
  return {
    name: 'N/A',
    description: 'N/A',
    type: 'N/A',
    required: false,
    ...withFields,
  }
}

export function newOsqueryTableSpec(
    withFields?: Partial<OsqueryTableSpec>,
): OsqueryTableSpec {
  return {
    name: 'N/A',
    description: 'N/A',
    columns: [],
    platforms: [],
    ...withFields,
  }
}
