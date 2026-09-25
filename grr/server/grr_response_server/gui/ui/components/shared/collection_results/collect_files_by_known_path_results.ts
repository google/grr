import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {
  CollectFilesByKnownPathResult,
  CollectFilesByKnownPathResultStatus,
} from '../../../lib/api/api_interfaces';
import {
  translateHashToHex,
  translateStatEntry,
} from '../../../lib/api/translation/flow';
import {CollectionResult} from '../../../lib/models/result';
import {checkExhaustive} from '../../../lib/utils';
import {
  CollectionState,
  CollectionStatus,
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';

function flowFileResultFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly FlowFileResult[] {
  return collectionResults.map((flowResult) => {
    const payload = flowResult.payload as CollectFilesByKnownPathResult;
    return {
      statEntry: translateStatEntry(payload.stat!),
      hashes: translateHashToHex(payload.hash ?? {}),
      status: collectionStatusFromCollectFilesByKnownPathResultStatus(
        payload.status,
      ),
      clientId: flowResult.clientId,
    };
  });
}

function collectionStatusFromCollectFilesByKnownPathResultStatus(
  status: CollectFilesByKnownPathResultStatus | undefined,
): CollectionStatus {
  if (!status) {
    return {state: CollectionState.UNKNOWN};
  }
  switch (status) {
    case CollectFilesByKnownPathResultStatus.COLLECTED:
      return {state: CollectionState.SUCCESS};
    case CollectFilesByKnownPathResultStatus.IN_PROGRESS:
      return {state: CollectionState.IN_PROGRESS};
    case CollectFilesByKnownPathResultStatus.NOT_FOUND:
      return {state: CollectionState.ERROR, message: 'File not found'};
    case CollectFilesByKnownPathResultStatus.FAILED:
      return {state: CollectionState.ERROR, message: 'Unknown error'};
    case CollectFilesByKnownPathResultStatus.UNDEFINED:
      return {state: CollectionState.UNKNOWN};
    default:
      checkExhaustive(status);
  }
}

/**
 * Component that displays results of CollectFilesByKnownPath flow.
 */
@Component({
  selector: 'collect-files-by-known-path-results',
  templateUrl: './collect_files_by_known_path_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, FileResultsTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectFilesByKnownPathResults {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    readonly FlowFileResult[],
    readonly CollectionResult[]
  >({
    transform: flowFileResultFromCollectionResults,
  });
}
