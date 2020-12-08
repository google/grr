import {Component, ViewEncapsulation, OnDestroy} from '@angular/core';
import {FormControl} from '@angular/forms';

import {Observable, Subject} from 'rxjs';
import {
  debounceTime,
  startWith,
  map,
  filter,
  distinctUntilChanged,
  takeUntil,
  shareReplay,
} from 'rxjs/operators';

import {allTableSpecs, nameToTable} from './osquery_table_specs';
import {isNonNull} from '@app/lib/preconditions';
import {constructSelectAllFromTable} from './query_composer';
import {
  tableCategoryFromNames,
  tableCategoryFromSpecs,
  CategoryWithMatchResults,
  TableCategoryWithMatchers,
  ValueWithMatcher,
  ValueWithMatchResult,
  MatchResultForTable,
} from './osquery_helper_interfaces';


/** A helper component for the OsqueryForm to aid in writing the query */
@Component({
  selector: 'osquery-query-helper',
  templateUrl: './osquery_query_helper.ng.html',
  styleUrls: ['./osquery_query_helper.scss'],

  // This makes all styles effectively global.
  encapsulation: ViewEncapsulation.None,
})
export class OsqueryQueryHelper implements OnDestroy {
  private static readonly INPUT_DEBOUNCE_TIME_MS = 50;
  readonly minCharactersToSearch = 2;

  private readonly unsubscribe$ = new Subject<void>();

  queryToReturn?: string;

  readonly searchControl = new FormControl('');

  private readonly searchValues$ = this.searchControl.valueChanges.pipe(
    filter(isNonNull),
    debounceTime(OsqueryQueryHelper.INPUT_DEBOUNCE_TIME_MS),
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
    // Without sharing the execution, unsubscribing and subscribing again will
    // produce an un-needed '' first value.
    shareReplay(1),
  );

  readonly queryToReturn$ = this.searchValues$.pipe(
      map((tableName) => {
        const tableSpec = nameToTable(tableName);

        if (isNonNull(tableSpec)) {
          return constructSelectAllFromTable(tableSpec);
        } else {
          return undefined;
        }
      }),
  );

  private readonly categoriesWithMatchers = [
      tableCategoryFromNames('Suggested', ['users', 'file']),
      tableCategoryFromSpecs('All tables', allTableSpecs),
  ];

  readonly filteredCategories: ReadonlyArray<
      Observable<CategoryWithMatchResults>
  > = this.categoriesWithMatchers.map(
      (categoryWithMatchers: TableCategoryWithMatchers) => {
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
      categoryWithMatchers: TableCategoryWithMatchers,
      keyword: string,
  ): CategoryWithMatchResults {
    const tablesMatchResults = categoryWithMatchers.tableSpecs.map(
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
        matchResult: undefined,
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
  ): MatchResultForTable | undefined {
    if (discardIfNothingMatches) {
      const noMatchInName = !isNonNull(nameMatch.matchResult);
      const noMatchInDescription = !isNonNull(descriptionMatch.matchResult);
      const noMatchInColumns = columnMatches.every(
          columnMatch => !isNonNull(columnMatch.matchResult),
      );

      if (noMatchInName && noMatchInDescription && noMatchInColumns) {
        return undefined;
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
