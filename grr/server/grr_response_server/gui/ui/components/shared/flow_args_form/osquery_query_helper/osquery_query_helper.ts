import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {toSignal} from '@angular/core/rxjs-interop';
import {FuzzyMatcher, Match} from '../../../../lib/fuzzy_matcher';
import {
  TableCategory,
  tableCategoryFromNames,
  tableCategoryFromSpecs,
  TableCategoryWithMatchMap,
} from './osquery_helper_model';
import {allTableSpecs, nameToTable} from './osquery_table_specs';
import {constructSelectAllFromTable} from './query_composer';
import {TableInfoItem} from './table_info_item';

/**
 * Names of tables that are suggested to the user when they start typing a query
 */
export const SUGGESTED_TABLE_NAMES = ['users', 'file'];

const TABLE_CATEGORIES = [
  tableCategoryFromNames('Suggested', SUGGESTED_TABLE_NAMES),
  tableCategoryFromSpecs('All tables', allTableSpecs),
];

/** A helper component for the OsqueryForm to aid in writing the query */
@Component({
  selector: 'osquery-query-helper',
  templateUrl: './osquery_query_helper.ng.html',
  styleUrls: ['./osquery_query_helper.scss'],
  imports: [
    CommonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatButtonModule,
    ReactiveFormsModule,
    TableInfoItem,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryQueryHelper {
  private readonly destroyRef = inject(DestroyRef);

  readonly searchControl = new FormControl('');

  private readonly searchControlSignal = toSignal(
    this.searchControl.valueChanges,
    {initialValue: ''},
  );

  private readonly fuzzyMatcher = new FuzzyMatcher(
    TABLE_CATEGORIES.map((category) => category.subjects).flat(),
  );

  readonly filteredCategories = computed<readonly TableCategoryWithMatchMap[]>(
    () => {
      const searchValue = this.searchControlSignal();
      let matchMap = new Map<string, Match>();
      if (searchValue) {
        const matches = this.fuzzyMatcher.match(searchValue);
        matchMap = new Map(matches.map((match) => [match.subject, match]));
      }

      const all = TABLE_CATEGORIES.map((tableCategory: TableCategory) => {
        if (searchValue === '') {
          // If the search is empty we want to display all
          // categories and tables, so we won't filter out
          // anything here.
          return {
            ...tableCategory,
            matchMap,
          };
        }
        return this.filterTablesInCategory(tableCategory, matchMap);
      });

      return all.filter(
        (categoryWithEligibleTables: TableCategoryWithMatchMap) => {
          return categoryWithEligibleTables.tableSpecs.length > 0;
        },
      );
    },
  );

  readonly queryToReturn = computed<string | undefined>(() => {
    const searchValue = this.searchControlSignal();
    if (searchValue == null) {
      return undefined;
    }
    const tableSpec = nameToTable(searchValue);
    if (tableSpec != null) {
      return constructSelectAllFromTable(tableSpec);
    } else {
      return undefined;
    }
  });

  private filterTablesInCategory(
    tableCategory: TableCategory,
    matchMap: Map<string, Match>,
  ): TableCategoryWithMatchMap {
    const eligibleTables = tableCategory.tableSpecs.filter((tableSpec) => {
      const nameMatch = matchMap.get(tableSpec.name);
      const descriptionMatch = matchMap.get(tableSpec.description);
      const columnMatches = tableSpec.columns.map((column) =>
        matchMap.get(column.name),
      );

      return (
        nameMatch != null ||
        descriptionMatch != null ||
        columnMatches.some((match) => match != null)
      );
    });

    return {
      ...tableCategory,
      tableSpecs: eligibleTables,
      matchMap,
    };
  }
}
