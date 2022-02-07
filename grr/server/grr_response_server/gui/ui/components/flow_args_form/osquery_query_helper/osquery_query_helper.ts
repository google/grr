import {Component, OnDestroy, ViewEncapsulation} from '@angular/core';
import {FormControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {debounceTime, distinctUntilChanged, filter, map, shareReplay, startWith, takeUntil,} from 'rxjs/operators';

import {FuzzyMatcher, Match} from '../../../lib/fuzzy_matcher';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';

import {TableCategory, tableCategoryFromNames, tableCategoryFromSpecs, TableCategoryWithMatchMap,} from './osquery_helper_model';
import {allTableSpecs, nameToTable, OsqueryTableSpec} from './osquery_table_specs';
import {constructSelectAllFromTable} from './query_composer';


/** A helper component for the OsqueryForm to aid in writing the query */
@Component({
  selector: 'osquery-query-helper',
  templateUrl: './osquery_query_helper.ng.html',
  styleUrls: ['./osquery_query_helper.scss'],

  // This makes all styles effectively global. We need that in order to style
  // the mat-autocomplete element. Its elements are placed at a different
  // place in the DOM not inside this component, and so style encapsulation
  // wouldn't allow our styles to reach them.
  // https://github.com/angular/components/issues/11764#issuecomment-400370834
  encapsulation: ViewEncapsulation.None,
})
export class OsqueryQueryHelper implements OnDestroy {
  private static readonly INPUT_DEBOUNCE_TIME_MS = 50;
  readonly minCharactersToSearch = 2;

  readonly ngOnDestroy = observeOnDestroy(this);

  readonly searchControl = new FormControl('');

  readonly searchValues$ = this.searchControl.valueChanges.pipe(
      filter(isNonNull),
      debounceTime(OsqueryQueryHelper.INPUT_DEBOUNCE_TIME_MS),
      map((searchValue: string) => {
        if (searchValue.length < this.minCharactersToSearch) {
          return '';
        } else {
          return searchValue;
        }
      }),
      startWith(''),
      distinctUntilChanged(),
      takeUntil(this.ngOnDestroy.triggered$),

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

  readonly suggestedTableNames = ['users', 'file'];
  private readonly tableCategories = [
    tableCategoryFromNames('Suggested', this.suggestedTableNames),
    tableCategoryFromSpecs('All tables', allTableSpecs),
  ];

  private readonly allStringToMatch: ReadonlyArray<string> =
      this.tableCategories.map(category => category.subjects).flat();
  private readonly fuzzyMatcher = new FuzzyMatcher(this.allStringToMatch);

  readonly filteredCategories$:
      Observable<ReadonlyArray<TableCategoryWithMatchMap>> =
          this.searchValues$.pipe(
              map(keyword => {
                const matchMap = this.computeMatchMap(keyword);

                const all =
                    this.tableCategories.map((tableCategory: TableCategory) => {
                      if (keyword === '') {
                        // If the search is empty we want to display all
                        // categories and tables, so we won't filter out
                        // anything here.
                        return {
                          ...tableCategory,
                          matchMap,
                        };
                      }

                      return this.filterTablesInCategory(
                          tableCategory,
                          matchMap,
                      );
                    });

                return all.filter(categoryWithEligibleTables => {
                  return categoryWithEligibleTables.tableSpecs.length > 0;
                });
              }),
          );

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
    const eligibleTables = tableCategory.tableSpecs.filter(tableSpec => {
      const nameMatch = matchMap.get(tableSpec.name);
      const descriptionMatch = matchMap.get(tableSpec.description);
      const columnMatches =
          tableSpec.columns.map(column => matchMap.get(column.name));

      return isNonNull(nameMatch) || isNonNull(descriptionMatch) ||
          columnMatches.some(isNonNull);
    });

    return {
      ...tableCategory,
      tableSpecs: eligibleTables,
      matchMap,
    };
  }

  trackCategoryByName(
      index: number,
      category: TableCategory,
      ): string {
    return category.categoryName;
  }

  trackTableSpecByName(
      index: number,
      tableSpec: OsqueryTableSpec,
      ): string {
    return tableSpec.name;
  }
}
