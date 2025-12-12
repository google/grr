import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {CollectLargeFileFlowResult as ApiCollectLargeFileFlowResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectLargeFileFlowResults} from './collect_large_file_flow_results';
import {CollectLargeFileFlowResultsHarness} from './testing/collect_large_file_flow_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(CollectLargeFileFlowResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectLargeFileFlowResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Large File Flow Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectLargeFileFlowResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no tables if there are no results', async () => {
    const {harness} = await createComponent([]);

    expect(await harness.tables()).toHaveSize(0);
  });

  it('shows a single result', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT,
        payload: {
          sessionUri: 'session-uri',
          totalBytesSent: '100',
        } as ApiCollectLargeFileFlowResult,
      }),
    ]);

    expect(await harness.tables()).toHaveSize(1);
    const table = (await harness.tables())[0];
    expect(await table.text()).toContain('session-uri');
    expect(await table.text()).toContain('100 B');
  });

  it('shows multiple results', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT,
        payload: {
          sessionUri: 'session-uri-1',
          totalBytesSent: '100',
        },
      }),
      newFlowResult({
        payloadType: PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT,
        payload: {
          sessionUri: 'session-uri-2',
          totalBytesSent: '200',
        },
      }),
    ]);

    expect(await harness.tables()).toHaveSize(2);
  });

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
