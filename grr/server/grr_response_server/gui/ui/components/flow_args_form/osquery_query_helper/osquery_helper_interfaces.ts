import {SingleElementFuzzyMatcher, Match} from '@app/lib/fuzzy_matcher';
import {OsqueryTableSpec, nameToTable} from './osquery_table_specs';
import {isNonNull} from '@app/lib/preconditions';

/** Holds a string with a matcher which can be used to "fuzzy match" it
 * against a keyword
 */
export interface ValueWithMatcher {
  readonly value: string;
  readonly matcher: SingleElementFuzzyMatcher;
}

/**
 * Holds the table name, table description and column names, together with
 * "fuzzy matchers" for them.
 */
export class TableSpecWithMatchers {
  readonly tableNameMatcher: ValueWithMatcher;
  readonly tableDescriptionMatcher: ValueWithMatcher;
  readonly columNameMatchers: ReadonlyArray<ValueWithMatcher>;

  constructor(tableSpec: OsqueryTableSpec) {
    this.tableNameMatcher = {
      value: tableSpec.name,
      matcher: new SingleElementFuzzyMatcher(tableSpec.name),
    };

    this.tableDescriptionMatcher = {
      value: tableSpec.description,
      matcher: new SingleElementFuzzyMatcher(tableSpec.description),
    };

    this.columNameMatchers = tableSpec.columns.map(
        column => ({
          value: column.name,
          matcher: new SingleElementFuzzyMatcher(column.name),
        }),
    );
  }
}

/**
 * Holds a table category name, together with all the Osquery table
 * specifications in this category (each containing a matcher for its values).
 */
export interface TableCategoryWithMatchers {
  readonly name: string;
  readonly tableSpecs: ReadonlyArray<TableSpecWithMatchers>;
}

/**
 * Given a table category name and Osquery table specs to put inside it,
 * the function creates matchers for the values inside the table specs and
 * packs everything into a table category with matchers.
 */
export function tableCategoryFromSpecs(
    categoryName: string,
    justTableSpecs: ReadonlyArray<OsqueryTableSpec>,
): TableCategoryWithMatchers {
  const tableSpecsWithMatchers = justTableSpecs.map(
      tableSpec => new TableSpecWithMatchers(tableSpec));
  return {
    name: categoryName,
    tableSpecs: tableSpecsWithMatchers,
  };
}

/**
 * Given a category name and an array of Osquery table names to put inside,
 * it looks up the table specifications, bundles them up with matchers, and
 * produces a table category with matchers.
 */
export function tableCategoryFromNames(
    categoryName: string,
    tableNames: ReadonlyArray<string>,
): TableCategoryWithMatchers {
  const justTableSpecs = tableNames.map(tableName => {
    const tableSpec = nameToTable(tableName);
    if (!isNonNull(tableSpec)) {
      throw Error(`Table not found: ${tableName} (category ${categoryName})`);
    }
    return tableSpec;
  });

  return tableCategoryFromSpecs(categoryName, justTableSpecs);
}

/** Holds a string with results from fuzzy-matching it against some keyword. */
export interface ValueWithMatchResult {
  readonly value: string;
  readonly matchResult?: Match;
}

/**
 * Table name, description and column values, bundled with results from
 * matching them against some keyword.
 */
export declare interface MatchResultForTable {
  name: ValueWithMatchResult;
  description: ValueWithMatchResult;
  columns: ReadonlyArray<ValueWithMatchResult>;
}

/**
 * Holds a category name and an array of table specification values with
 * results from matching those values against some keyword.
 */
export interface CategoryWithMatchResults {
  readonly name: string;
  readonly tablesMatchResults: ReadonlyArray<MatchResultForTable>;
}
