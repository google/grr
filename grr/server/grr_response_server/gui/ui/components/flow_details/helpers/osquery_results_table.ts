import { Component, ChangeDetectionStrategy, Input } from '@angular/core';
import { OsqueryTable } from '@app/lib/api/api_interfaces';

/**
 * Component that displays the details (status, errors, results) for a particular Osquery Flow.
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
}
