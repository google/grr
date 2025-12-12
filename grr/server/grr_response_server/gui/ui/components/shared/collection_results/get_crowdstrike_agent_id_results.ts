import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {GetCrowdstrikeAgentIdResult} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';

/**
 * Component that shows `GetCrowdstrikeAgentIdResult` flow results.
 */
@Component({
  selector: 'get-crowdstrike-agent-id-results',
  templateUrl: './get_crowdstrike_agent_id_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GetCrowdstrikeAgentIdResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected getCrowdstrikeAgentIdResultFromCollectionResult(
    result: CollectionResult,
  ): GetCrowdstrikeAgentIdResult {
    return result.payload as GetCrowdstrikeAgentIdResult;
  }
}
