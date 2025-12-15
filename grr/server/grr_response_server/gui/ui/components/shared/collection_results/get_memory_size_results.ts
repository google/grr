import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {GetMemorySizeResult as ApiGetMemorySizeResult} from '../../../lib/api/api_interfaces';
import {translateGetMemorySizeResult} from '../../../lib/api/translation/flow';
import {GetMemorySizeResult} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';
import {CopyButton} from '../copy_button';

/**
 * Component that shows `GetMemorySizeResult` flow results.
 */
@Component({
  selector: 'get-memory-size-results',
  templateUrl: './get_memory_size_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton, HumanReadableByteSizePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GetMemorySizeResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected getMemorySizeResultFromCollectionResult(
    result: CollectionResult,
  ): GetMemorySizeResult {
    return translateGetMemorySizeResult(
      result.payload as ApiGetMemorySizeResult,
    );
  }
}
