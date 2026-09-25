import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {GetMemorySizeResult as ApiGetMemorySizeResult} from '../../../lib/api/api_interfaces';
import {translateGetMemorySizeResult} from '../../../lib/api/translation/flow';
import {GetMemorySizeResult} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';

function getMemorySizeResultsFromCollectionResults(
  results: readonly CollectionResult[],
): readonly GetMemorySizeResult[] {
  return results
    .map((item) => item.payload as ApiGetMemorySizeResult)
    .map(translateGetMemorySizeResult);
}

/**
 * Component that shows `GetMemorySizeResult` flow results.
 */
@Component({
  selector: 'get-memory-size-results',
  templateUrl: './get_memory_size_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, HumanReadableByteSizePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GetMemorySizeResults {
  readonly collectionResults = input.required<
    readonly GetMemorySizeResult[],
    readonly CollectionResult[]
  >({
    transform: getMemorySizeResultsFromCollectionResults,
  });
}
