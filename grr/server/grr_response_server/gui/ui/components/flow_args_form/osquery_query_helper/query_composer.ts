/** Provides functionality for composing SQL queries from Osquery table spces */
import {OsqueryTableSpec} from './osquery_table_specs';

function constructFromClause(table: OsqueryTableSpec): string {
  return `FROM ${table.name}`
}

function constructSelectClause(table: OsqueryTableSpec): string {
  const allColumnNames = table.columns.map(column => column.name);
  const columnsWithSeparator = allColumnNames.join(',\n\t');
  return `SELECT\n\t${columnsWithSeparator}`;
}

function constructWhereClause(table: OsqueryTableSpec): string {
  const requiredColumnNames = table.columns
    .filter(column => column.required)
    .map(column => column.name);
  if (requiredColumnNames.length === 0) {
    return '';
  }

  const comment = 'TODO: Set required field as appropriate.'
  const columnConstraints = requiredColumnNames.map(
      colName => `${colName} LIKE "" -- ${comment}`);
  const whereClauseArgs = columnConstraints.join('\nAND\n\t');

  return `WHERE\n\t${whereClauseArgs}`;
}

export function constructSelectAllFromTable(table: OsqueryTableSpec): string {
  const selectClause = constructSelectClause(table);
  const fromClause = constructFromClause(table);
  const whereClause = constructWhereClause(table);

  return [selectClause, fromClause, whereClause, ';']
    .filter(clause => clause !== '')
    .join('\n');
}
