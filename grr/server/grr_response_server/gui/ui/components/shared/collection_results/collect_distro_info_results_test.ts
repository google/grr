import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {CollectDistroInfoResult as ApiCollectDistroInfoResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectDistroInfoResults} from './collect_distro_info_results';
import {CollectDistroInfoResultsHarness} from './testing/collect_distro_info_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(CollectDistroInfoResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectDistroInfoResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Distro Info Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectDistroInfoResults, NoopAnimationsModule],
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
        payloadType: PayloadType.COLLECT_DISTRO_INFO_RESULT,
        payload: {
          name: 'banana',
          release: 'apple',
          versionMajor: 111,
          versionMinor: 222,
        } as ApiCollectDistroInfoResult,
      }),
    ]);

    expect(await harness.tables()).toHaveSize(1);
    const table = (await harness.tables())[0];
    expect(await table.text()).toContain('banana');
    expect(await table.text()).toContain('apple');
    expect(await table.text()).toContain('111');
    expect(await table.text()).toContain('222');
  });

  it('shows multiple results', async () => {
    const payload: ApiCollectDistroInfoResult = {
      name: 'distro',
      release: 'release',
      versionMajor: 1,
      versionMinor: 2,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_DISTRO_INFO_RESULT,
        payload,
      }),
      newFlowResult({
        payloadType: PayloadType.COLLECT_DISTRO_INFO_RESULT,
        payload,
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

    expect(await harness.clientIds()).toHaveSize(0);
  });
});
