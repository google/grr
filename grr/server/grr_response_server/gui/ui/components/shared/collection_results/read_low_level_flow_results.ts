import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {ReadLowLevelFlowResult as ApiReadLowLevelFlowResult} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';

/** Component that displays `ReadLowLevel` flow results. */
@Component({
  selector: 'read-low-level-flow-results',
  templateUrl: './read_low_level_flow_results.ng.html',
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReadLowLevelFlowResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = computed(() => {
    return this.collectionResults().some(isHuntResult);
  });

  protected readonly pathsPerClientId = computed<Map<string, string[]>>(() => {
    const pathsPerClientId = new Map<string, string[]>();
    for (const collectionResult of this.collectionResults()) {
      const path = this.readLowLevelFlowResultFromFlowResult(collectionResult);
      if (!pathsPerClientId.has(collectionResult.clientId)) {
        pathsPerClientId.set(collectionResult.clientId, []);
      }
      pathsPerClientId.get(collectionResult.clientId)!.push(path);
    }
    return pathsPerClientId;
  });

  protected readLowLevelFlowResultFromFlowResult(
    collectionResult: CollectionResult,
  ): string {
    const result = collectionResult.payload as ApiReadLowLevelFlowResult;
    return result.path ?? '';
  }
}
