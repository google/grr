import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {OsqueryResult as ApiOsqueryResult} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {
  OsqueryRow,
  OsqueryTable,
  OsqueryTableData,
} from './data_renderer/osquery_table';

function osqueryTablesFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly OsqueryTableData[] {
  return collectionResults.map((flowResult) => {
    const table = (flowResult.payload as ApiOsqueryResult).table;
    const rows: OsqueryRow[] = [];
    for (const row of table?.rows ?? []) {
      rows.push({
        clientId: flowResult.clientId,
        values: row.values,
      });
    }
    return {
      query: table?.query ?? '',
      header: table?.header,
      rows,
    };
  });
}

/**
 * Component to display `OsqueryResult` collection results.
 */
@Component({
  selector: 'osquery-results',
  templateUrl: './osquery_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, OsqueryTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly isHuntResult = computed<boolean>(() => {
    return this.collectionResults().some(isHuntResult);
  });

  readonly osqueryTables = computed<readonly OsqueryTableData[]>(() => {
    return osqueryTablesFromCollectionResults(this.collectionResults());
  });
}
