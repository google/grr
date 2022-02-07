import {Match} from '../../../lib/fuzzy_matcher';
import {isNonNull} from '../../../lib/preconditions';

import {nameToTable, OsqueryColumnSpec, OsqueryTableSpec} from './osquery_table_specs';

/**
 * Holds a table category name, all the Osquery table
 * specifications in this category, and all string subjects that are relevant
 * for fuzzy-matching.
 */
export interface TableCategory {
  readonly categoryName: string;
  readonly tableSpecs: ReadonlyArray<OsqueryTableSpec>;
  readonly subjects: ReadonlyArray<string>;
}

/**
 * Same as {@link TableCategory}, but also holds a mapping from string subjects
 * to match results.
 */
export interface TableCategoryWithMatchMap extends TableCategory {
  readonly matchMap: Map<string, Match>;
}

function columnSpecsToSubjects(
    columnSpecs: ReadonlyArray<OsqueryColumnSpec>,
    ): ReadonlyArray<string> {
  return columnSpecs.map(column => column.name);
}

function tableSpecsToSubjects(
    tableSpecs: ReadonlyArray<OsqueryTableSpec>,
    ): ReadonlyArray<string> {
  const names = tableSpecs.map(spec => spec.name);
  const descriptions = tableSpecs.map(spec => spec.description);
  const columns = tableSpecs.map(spec => columnSpecsToSubjects(spec.columns));
  return [
    ...names,
    ...descriptions,
    ...columns.flat(),
  ];
}

/**
 * Returns a string array with all strings inside a table category to be
 * considered for matching. Those are: category name, table names, table
 * descriptions, and the names of all table columns.
 */
export function tableCategoryToSubjects(
    category: TableCategory,
    ): ReadonlyArray<string> {
  return [
    category.categoryName,
    ...tableSpecsToSubjects(category.tableSpecs),
  ];
}

/**
 * Given a table category name and Osquery table specs to put inside it,
 * the function extracts all relevant subjects for future fuzzy matching and
 * packs everything into a table category.
 */
export function tableCategoryFromSpecs(
    categoryName: string,
    tableSpecs: ReadonlyArray<OsqueryTableSpec>,
    ): TableCategory {
  const subjects = [
    categoryName,
    ...tableSpecsToSubjects(tableSpecs),
  ];

  return {
    categoryName,
    tableSpecs,
    subjects,
  };
}

/**
 * Given a category name and an array of Osquery table names to put inside,
 * it looks up the table specifications, finds the relevant subject strings for
 * fuzzy matching and bundles everything together.
 */
export function tableCategoryFromNames(
    categoryName: string,
    tableNames: ReadonlyArray<string>,
    ): TableCategory {
  const tableSpecs = tableNames.map(tableName => {
    const tableSpec = nameToTable(tableName);
    if (!isNonNull(tableSpec)) {
      throw new Error(
          `Table not found: ${tableName} (category ${categoryName})`);
    }
    return tableSpec;
  });

  return tableCategoryFromSpecs(categoryName, tableSpecs);
}
