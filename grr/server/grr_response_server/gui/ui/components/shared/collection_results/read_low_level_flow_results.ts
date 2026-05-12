import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {ReadLowLevelFlowResult as ApiReadLowLevelFlowResult} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';

function readLowLevelFlowResultsFromFlowResults(
  collectionResults: readonly CollectionResult[],
): readonly string[] {
  return collectionResults
    .map((item) => item.payload as ApiReadLowLevelFlowResult)
    .map((res) => res.path)
    .filter((path): path is string => !!path);
}

/** Component that displays `ReadLowLevel` flow results. */
@Component({
  selector: 'read-low-level-flow-results',
  templateUrl: './read_low_level_flow_results.ng.html',
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReadLowLevelFlowResults {
  readonly collectionResults = input.required<
    readonly string[],
    readonly CollectionResult[]
  >({
    transform: readLowLevelFlowResultsFromFlowResults,
  });
}
