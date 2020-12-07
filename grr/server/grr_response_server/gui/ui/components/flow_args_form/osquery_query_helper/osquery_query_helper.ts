import {Component, ViewEncapsulation, OnDestroy} from '@angular/core';
import {FormControl} from '@angular/forms';

import {Observable, Subject, ReplaySubject} from 'rxjs';
import {debounceTime, startWith, map, filter, distinctUntilChanged, takeUntil} from 'rxjs/operators';

import {allTableSpecs, OsqueryTableSpec, nameToTable} from './osquery_table_specs';
import {isNonNull} from '@app/lib/preconditions';
import {SingleElementFuzzyMatcher, Match} from '@app/lib/fuzzy_matcher';
import {MatchResultForTable} from './table_info_item/table_info_item';

/** Provides functionality for composing SQL queries from Osquery table spces */
export class QueryComposer {
  static constructFromClause(table: OsqueryTableSpec): string {
    return `FROM ${table.name}`
  }

  static constructSelectClause(table: OsqueryTableSpec): string {
    const allColumnNames = table.columns.map(column => column.name);
    const columnsWithSeparator = allColumnNames.join(',\n\t');
    return `SELECT\n\t${columnsWithSeparator}`;
  }

  static constructWhereClause(table: OsqueryTableSpec): string {
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

  static constructSelectAllFromTable(table: OsqueryTableSpec): string {
    const selectClause = QueryComposer.constructSelectClause(table);
    const fromClause = QueryComposer.constructFromClause(table);
    const whereClause = QueryComposer.constructWhereClause(table);

    return [selectClause, fromClause, whereClause, ';']
      .filter(clause => clause !== '')
      .join('\n');
  }
}

/**
 * Data structure which holds a table category name and the Osquery tables specs inside.
 */
class TableCategory {
  private constructor(
      public name: string,
      public tableSpecs: ReadonlyArray<OsqueryTableSpec>,
  ) { }

  static fromTableSpecs(
    name: string,
    tableSpecs: ReadonlyArray<OsqueryTableSpec>,
  ): TableCategory {
    return new TableCategory(name, tableSpecs);
  }

  static fromTableNames(
    categoryName: string,
    tableNames: ReadonlyArray<string>,
  ): TableCategory {
    const tableSpecs = tableNames.map(tableName => {
      const tableSpec = nameToTable(tableName);
      if (!isNonNull(tableSpec)) {
        throw Error(`Table not found: ${tableName} (category ${categoryName})`);
      }
      return tableSpec;
    });

    return new TableCategory(categoryName, tableSpecs);
  }
}

declare interface ValueWithMatcher {
  readonly value: string;
  readonly matcher: SingleElementFuzzyMatcher;
}

class TableSpecWithMatchers {
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

class CategoryWithMatchers {
  constructor(
      public name: string,
      public tableSpecsWithMatchers: ReadonlyArray<TableSpecWithMatchers>,
  ) { }

  static fromTableCategory(tableCategory: TableCategory) {
    const tableSpecsWithMatchers = tableCategory.tableSpecs.map(
      tableSpec => new TableSpecWithMatchers(tableSpec),
    );

    return new CategoryWithMatchers(
        tableCategory.name,
        tableSpecsWithMatchers,
    );
  }
}

declare interface CategoryWithMatchResults {
  readonly name: string;
  readonly tablesMatchResults: ReadonlyArray<MatchResultForTable>;
}

export declare interface ValueWithMatchResult {
  readonly value: string;
  readonly matchResult: Match | null;
}

/** A helper component for the OsqueryForm to aid in writing the query */
@Component({
  selector: 'osquery-query-helper',
  templateUrl: './osquery_query_helper.ng.html',
  styleUrls: ['./osquery_query_helper.scss'],

  // This makes all styles effectively global.
  encapsulation: ViewEncapsulation.None,
})
export class OsqueryQueryHelper implements OnDestroy {
  private static readonly INPUT_DEVOUNCE_TIME_MS = 50;
  readonly minCharactersToSearch = 2;

  private readonly unsubscribe$ = new Subject<void>();

  queryToReturn?: string;

  readonly searchControl = new FormControl('');

  /**
   * We use Subject instead of Observable because searchValues$ or derivatives
   * of it are subscribed to multiple times (e.g. with | async pipes), but we
   * don't want to create a separate execution for every subscription.
   */
  private readonly searchValues$ = new ReplaySubject<string>(1);

  constructor() {
    this.searchControl.valueChanges.pipe(
        filter(isNonNull),
        debounceTime(OsqueryQueryHelper.INPUT_DEVOUNCE_TIME_MS),
        map(searchValue => {
          if (searchValue.length < this.minCharactersToSearch) {
            return '';
          } else {
            return searchValue;
          }
        }),
        startWith(''),
        distinctUntilChanged(),

        takeUntil(this.unsubscribe$),
    ).subscribe(
        searchValue => {
          return this.searchValues$.next(searchValue);
        }
    );
  }

  readonly queryToReturn$ = this.searchValues$.pipe(
      map((tableName) => {
        const tableSpec = nameToTable(tableName);

        if (isNonNull(tableSpec)) {
          return QueryComposer.constructSelectAllFromTable(tableSpec);
        } else {
          return null;
        }
      }),
  );

  private readonly tableCategories = [
      TableCategory.fromTableNames('Suggested', ['users', 'file']),
      TableCategory.fromTableSpecs('All tables', allTableSpecs),
  ];

  private readonly categoriesWithMatchers = this.tableCategories.map(
      tableCategory => CategoryWithMatchers.fromTableCategory(tableCategory),
  );

  readonly filteredCategories: ReadonlyArray<
      Observable<CategoryWithMatchResults>
  > = this.categoriesWithMatchers.map(
      (categoryWithMatchers: CategoryWithMatchers) => {
        return this.searchValues$.pipe(
            map(keyword => {
              return this.getMatchingTablesInCategory(
                  categoryWithMatchers,
                  keyword,
              );
            }),
        );
      }
  );

  private getMatchingTablesInCategory(
      categoryWithMatchers: CategoryWithMatchers,
      keyword: string,
  ): CategoryWithMatchResults {
    const tablesMatchResults = categoryWithMatchers.tableSpecsWithMatchers.map(
        tableWithMatchers => {
          const nameMatchResult = this.matchValue(
              tableWithMatchers.tableNameMatcher,
              keyword,
          );
          const descriptionMatchResult = this.matchValue(
              tableWithMatchers.tableDescriptionMatcher,
              keyword,
          );
          const columnMatchResults = tableWithMatchers.columNameMatchers.map(
              columnMatcher => this.matchValue(columnMatcher, keyword)
          );

          return this.getMatchResultForTable(
              nameMatchResult,
              descriptionMatchResult,
              columnMatchResults,
              keyword !== '',
          );
        }).filter(
            isNonNull
        );

    return {
      name: categoryWithMatchers.name,
      tablesMatchResults,
    };
  }

  private matchValue(
      valueWithMatcher: ValueWithMatcher,
      keyword: string,
  ): ValueWithMatchResult {
    if (keyword === '') {
      return {
        value: valueWithMatcher.value,
        matchResult: null,
      };
    }

    const matchResult = valueWithMatcher.matcher.matchSingle(keyword);
    return {
      value: valueWithMatcher.value,
      matchResult,
    };
  }

  private getMatchResultForTable(
      nameMatch: ValueWithMatchResult,
      descriptionMatch: ValueWithMatchResult,
      columnMatches: ReadonlyArray<ValueWithMatchResult>,
      discardIfNothingMatches: boolean,
  ): MatchResultForTable | null {
    if (discardIfNothingMatches) {
      const noMatchInName = !isNonNull(nameMatch.matchResult);
      const noMatchInDescription = !isNonNull(descriptionMatch.matchResult);
      const noMatchInColumns = columnMatches.every(
          columnMatch => !isNonNull(columnMatch.matchResult),
      );

      if (noMatchInName && noMatchInDescription && noMatchInColumns) {
        return null;
      }
    }

    return {
      name: nameMatch,
      description: descriptionMatch,
      columns: columnMatches,
    };
  }

  ngOnDestroy(): void {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  trackCategoryWithResultsByName(
      _index: number,
      category: CategoryWithMatchResults,
  ): string {
    return category.name;
  }

  trackMatchResultByTableName(
      _index: number,
      matchResult: MatchResultForTable,
  ): string {
    return matchResult.name.value;
  }
}
