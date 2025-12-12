import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {CollectMultipleFilesResult} from '../../../lib/api/api_interfaces';
import {
  translateHashToHex,
  translateStatEntry,
} from '../../../lib/api/translation/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';

function flowFileResultsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly FlowFileResult[] {
  return collectionResults.map((item) => {
    const payload = item.payload as CollectMultipleFilesResult;
    return {
      statEntry: translateStatEntry(payload.stat!),
      hashes: translateHashToHex(payload.hash ?? {}),
      clientId: item.clientId,
    };
  });
}

/** Component that displays `CollectMultipleFiles` flow results. */
@Component({
  selector: 'collect-multiple-files-results',
  templateUrl: './collect_multiple_files_results.ng.html',
  imports: [CommonModule, FileResultsTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesResults {
  collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = computed(() => {
    return this.collectionResults().some(isHuntResult);
  });

  protected flowFileResults = computed(() => {
    return flowFileResultsFromCollectionResults(this.collectionResults());
  });
}
