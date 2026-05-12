import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CollectLargeFileFlowResult as ApiCollectLargeFileFlowResult} from '../../../lib/api/api_interfaces';
import {translateCollectLargeFileFlowResult} from '../../../lib/api/translation/flow';
import {CollectLargeFileFlowResult} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';

function collectLargeFileFlowResultsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly CollectLargeFileFlowResult[] {
  return collectionResults
    .map((res) => {
      return res.payload as ApiCollectLargeFileFlowResult;
    })
    .map(translateCollectLargeFileFlowResult);
}

/** Component that displays `CollectLargeFileFlowResult` flow results. */
@Component({
  selector: 'collect-large-file-flow-results',
  templateUrl: './collect_large_file_flow_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, HumanReadableByteSizePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectLargeFileFlowResults {
  collectionResults = input.required<
    readonly CollectLargeFileFlowResult[],
    readonly CollectionResult[]
  >({
    transform: collectLargeFileFlowResultsFromCollectionResults,
  });
}
