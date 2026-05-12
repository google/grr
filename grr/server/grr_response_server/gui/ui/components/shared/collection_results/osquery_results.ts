import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {
  OsqueryResult as ApiOsqueryResult,
  OsqueryTable as ApiOsqueryTable,
} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {OsqueryTable} from './data_renderer/osquery_table';

function osqueryTablesFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ApiOsqueryTable[] {
  return collectionResults.map(
    (flowResult) => (flowResult.payload as ApiOsqueryResult).table ?? {},
  );
}

/**
 * Component to display `OsqueryResult` flow results.
 */
@Component({
  selector: 'osquery-results',
  templateUrl: './osquery_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, OsqueryTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryResults {
  readonly collectionResults = input.required<
    readonly ApiOsqueryTable[],
    readonly CollectionResult[]
  >({
    transform: osqueryTablesFromCollectionResults,
  });
}
