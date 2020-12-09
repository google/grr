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

import {allTableSpecs, nameToTable, OsqueryTableSpec} from './osquery_table_specs';
import {isNonNull} from '@app/lib/preconditions';
import {constructSelectAllFromTable} from './query_composer';
import {
  tableCategoryFromNames,
  tableCategoryFromSpecs,
  tableCategoryToSubjects,
  TableCategory,
  TableCategoryWithMatchMap,
  FilteredCategories,
} from './osquery_helper_interfaces';
import { FuzzyMatcher, Match, stringWithHighlightsFromMatch } from '@app/lib/fuzzy_matcher';


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

  readonly searchValues$ = this.searchControl.valueChanges.pipe(
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

  private readonly tableCategories = [
      tableCategoryFromNames('Suggested', ['users', 'file']),
      tableCategoryFromSpecs('All tables', allTableSpecs),
  ];

  private readonly allStringToMatch: ReadonlyArray<string> =
      this.tableCategories.map(category => category.subjects).flat();
  private readonly fuzzyMatcher = new FuzzyMatcher(this.allStringToMatch);

  getFilteredCategories(
      keyword: string,
  ): ReadonlyArray<TableCategoryWithMatchMap> {
    const matchMap = this.computeMatchMap(keyword);

    const all = this.tableCategories.map((tableCategory: TableCategory) => {
      if (keyword === '') {
        // If the search is empty we want to display all categories and tables,
        // so we don't filter out anything.
        return {
          ...tableCategory,
          matchMap,
        }
      }

      return this.filterTablesInCategory(
          tableCategory,
          matchMap,
      );
    });

    return all.filter(categoryWithEligibleTables =>
        categoryWithEligibleTables.tableSpecs.length > 0);
  }

  private computeMatchMap(keyword: string): Map<string, Match> {
    if (keyword === '') {
      return new Map<string, Match>();
    }

    const matches = this.fuzzyMatcher.match(keyword);
    return new Map(matches.map(match => [match.subject, match]));
  }

  private filterTablesInCategory(
      tableCategory: TableCategory,
      matchMap: Map<string, Match>,
  ): TableCategoryWithMatchMap {
    const eligibleTables = tableCategory.tableSpecs.filter(
        tableSpec => {
          const nameMatch = matchMap.get(tableSpec.name);
          const descriptionMatch = matchMap.get(tableSpec.description);
          const columnMatches = tableSpec.columns.map(
              column => matchMap.get(column.name));

          return isNonNull(nameMatch) || isNonNull(descriptionMatch) ||
              columnMatches.some(isNonNull);
        });

    return {
      ...tableCategory,
      tableSpecs: eligibleTables,
      matchMap,
    };
  }

  ngOnDestroy(): void {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  trackCategoryByName(
      _index: number,
      category: TableCategory,
  ): string {
    return category.categoryName;
  }

  trackTableSpecByName(
      _index: number,
      tableSpec: OsqueryTableSpec,
  ): string {
    return tableSpec.name;
  }
}
