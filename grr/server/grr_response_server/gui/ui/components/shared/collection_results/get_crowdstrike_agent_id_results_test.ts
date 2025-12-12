import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {GetCrowdstrikeAgentIdResult as ApiGetCrowdstrikeAgentIdResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {GetCrowdstrikeAgentIdResults} from './get_crowdstrike_agent_id_results';
import {GetCrowdstrikeAgentIdResultsHarness} from './testing/get_crowdstrike_agent_id_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(GetCrowdstrikeAgentIdResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    GetCrowdstrikeAgentIdResultsHarness,
  );

  return {fixture, harness};
}

describe('Get Crowdstrike Agent ID Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [GetCrowdstrikeAgentIdResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows a single agent ID', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT,
        payload: {
          agentId: 'agent-id',
        } as ApiGetCrowdstrikeAgentIdResult,
      }),
    ]);

    const agentIds = await harness.agentIds();
    expect(agentIds).toHaveSize(1);
    expect(await agentIds[0].text()).toContain('agent-id');
  }));

  it('shows multiple file finder results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT,
        payload: {} as ApiGetCrowdstrikeAgentIdResult,
      }),
      newFlowResult({
        payloadType: PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT,
        payload: {} as ApiGetCrowdstrikeAgentIdResult,
      }),
    ]);

    const agentIds = await harness.agentIds();
    expect(agentIds).toHaveSize(2);
  }));

  it('shows client id for hunt results', async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payload: {
          clientId: 'C.1234',
        },
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(1);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
  });

  it('does not show client id for flow results', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payload: {
          clientId: 'C.1234',
        },
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(0);
  });
});
