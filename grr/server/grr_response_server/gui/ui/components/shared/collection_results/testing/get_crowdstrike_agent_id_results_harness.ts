import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the GetCrowdstrikeAgentIdResults component. */
export class GetCrowdstrikeAgentIdResultsHarness extends ComponentHarness {
  static hostSelector = 'get-crowdstrike-agent-id-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly agentIds = this.locatorForAll('.agent-id');
}
