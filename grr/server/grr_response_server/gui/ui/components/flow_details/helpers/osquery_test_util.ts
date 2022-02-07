import {DebugElement} from '@angular/core';
import {By} from '@angular/platform-browser';

import {OsqueryTable} from '../../../lib/api/api_interfaces';

/** Helper data structure to parse an osquery_results_table */
export class OsqueryResultsTableDOM {
  readonly queryDiv = this.rootElement?.query(By.css('.results-query-text'));
  readonly queryText = this.queryDiv?.nativeElement.innerText;

  readonly columnElements = this.rootElement?.queryAll(By.css('th'));
  readonly columnsText?: ReadonlyArray<string> = this.columnElements?.map(
      columnElement => columnElement.nativeElement.innerText);

  readonly cellDivs = this.rootElement?.queryAll(By.css('td'));
  readonly cellsText?: ReadonlyArray<string> =
      this.cellDivs?.map(cellDiv => cellDiv.nativeElement.innerText);

  get rowsLength() {
    return this.rootElement?.queryAll(By.css('tr')).length;
  }

  readonly errorDiv = this.rootElement?.query(By.css('.error'));
  readonly errorText = this.errorDiv?.nativeElement.innerText;

  constructor(private readonly rootElement?: DebugElement) {}
}

/**
 * Builds an OsqueryTable
 * @param query The Osquery query which produced this table
 * @param columns Column names of the table
 * @param rows Array of arrays containing values for each row
 */
export function newOsqueryTable(
    query: string,
    columns: ReadonlyArray<string>,
    rows: ReadonlyArray<ReadonlyArray<string>>,
    ): OsqueryTable {
  return {
    query,
    header: {
      columns: columns.map(colName => ({name: colName})),
    },
    rows: rows.map(rowValues => ({values: rowValues})),
  };
}
