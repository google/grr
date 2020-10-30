import { Component, ChangeDetectionStrategy, Input } from '@angular/core';
import { OsqueryTable } from '@app/lib/api/api_interfaces';

/**
 * Component that displays an OsqueryTable object as a HTML table.
 */
@Component({
  selector: 'osquery-results-table',
  templateUrl: './osquery_results_table.ng.html',
  styleUrls: ['./osquery_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryResultsTable {
  @Input()
  tableToDisplay?: OsqueryTable;

  trackByIndex(index: number, item: unknown): number {
    return index;
  }
}
