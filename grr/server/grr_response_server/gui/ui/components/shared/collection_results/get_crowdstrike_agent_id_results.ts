import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {GetCrowdstrikeAgentIdResult} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';

function getCrowdstrikeAgentIdResultsFromCollectionResults(
  results: readonly CollectionResult[],
): readonly GetCrowdstrikeAgentIdResult[] {
  return results.map((item) => item.payload as GetCrowdstrikeAgentIdResult);
}

/**
 * Component that shows `GetCrowdstrikeAgentIdResult` flow results.
 */
@Component({
  selector: 'get-crowdstrike-agent-id-results',
  templateUrl: './get_crowdstrike_agent_id_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GetCrowdstrikeAgentIdResults {
  readonly collectionResults = input.required<
    readonly GetCrowdstrikeAgentIdResult[],
    readonly CollectionResult[]
  >({
    transform: getCrowdstrikeAgentIdResultsFromCollectionResults,
  });
}
