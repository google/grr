import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {OsqueryTable} from '@app/lib/api/api_interfaces';
import {isNonNull} from '@app/lib/preconditions';

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
  @Input() table?: OsqueryTable;

  get atLeastOneRowPresent(): boolean {
    const rowCount = this.table?.rows?.length;
    return isNonNull(rowCount) && rowCount > 0;
  }

  trackByIndex(index: number, {}): number {
    return index;
  }
}
