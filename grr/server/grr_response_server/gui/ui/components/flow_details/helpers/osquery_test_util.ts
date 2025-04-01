import {DebugElement} from '@angular/core';
import {By} from '@angular/platform-browser';

import {OsqueryTable} from '../../../lib/api/api_interfaces';

/** Helper data structure to parse an osquery_results_table */
export class OsqueryResultsTableDOM {
  readonly queryDiv: DebugElement | undefined;
  readonly queryText: string | undefined;

  readonly columnElements: DebugElement[] | undefined;
  readonly columnsText?: readonly string[];

  readonly cellDivs: DebugElement[] | undefined;
  readonly cellsText?: readonly string[];

  get rowsLength() {
    return this.rootElement?.queryAll(By.css('tr')).length;
  }

  readonly errorDiv: DebugElement | undefined;
  readonly errorText: string | undefined;

  constructor(private readonly rootElement?: DebugElement) {
    this.queryDiv = this.rootElement?.query(By.css('.results-query-text'));
    this.queryText = this.queryDiv?.nativeElement.innerText;
    this.columnElements = this.rootElement?.queryAll(By.css('th'));
    this.columnsText = this.columnElements?.map(
      (columnElement) => columnElement.nativeElement.innerText,
    );
    this.cellDivs = this.rootElement?.queryAll(By.css('td'));
    this.cellsText = this.cellDivs?.map(
      (cellDiv) => cellDiv.nativeElement.innerText,
    );
    this.errorDiv = this.rootElement?.query(By.css('.error'));
    this.errorText = this.errorDiv?.nativeElement.innerText;
  }
}

/**
 * Builds an OsqueryTable
 * @param query The Osquery query which produced this table
 * @param columns Column names of the table
 * @param rows Array of arrays containing values for each row
 */
export function newOsqueryTable(
  query: string,
  columns: readonly string[],
  rows: ReadonlyArray<readonly string[]>,
): OsqueryTable {
  return {
    query,
    header: {
      columns: columns.map((colName) => ({name: colName})),
    },
    rows: rows.map((rowValues) => ({values: rowValues})),
  };
}
