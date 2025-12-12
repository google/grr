import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ReadLowLevelFlowResult as ApiReadLowLevelFlowResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ReadLowLevelFlowResults} from './read_low_level_flow_results';
import {ReadLowLevelFlowResultsHarness} from './testing/read_low_level_flow_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ReadLowLevelFlowResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ReadLowLevelFlowResultsHarness,
  );

  return {fixture, harness};
}

describe('Read Low Level Flow Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ReadLowLevelFlowResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows items if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.listedFiles()).toHaveSize(0);
  }));

  it('shows a single collection result', fakeAsync(async () => {
    const readLowLevelFlowResult: ApiReadLowLevelFlowResult = {
      path: '/foo',
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
        payload: readLowLevelFlowResult,
      }),
    ]);

    const listedFiles = await harness.listedFiles();
    expect(listedFiles).toHaveSize(1);
    expect(await listedFiles[0].text()).toBe('/foo');
  }));

  it('shows multiple results', fakeAsync(async () => {
    const readLowLevelFlowResult: ApiReadLowLevelFlowResult = {
      path: '/foo/bar',
    };
    const readLowLevelFlowResult2: ApiReadLowLevelFlowResult = {
      path: '/foo/baz',
    };
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
        payload: readLowLevelFlowResult,
      }),
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
        payload: readLowLevelFlowResult2,
      }),
    ]);

    const listedFiles = await harness.listedFiles();
    expect(listedFiles).toHaveSize(2);
    expect(await listedFiles[0].text()).toBe('/foo/bar');
    expect(await listedFiles[1].text()).toBe('/foo/baz');
  }));

  it('shows client ids for hunt results', fakeAsync(async () => {
    const readLowLevelFlowResult: ApiReadLowLevelFlowResult = {
      path: '/foo',
    };
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
        payload: readLowLevelFlowResult,
      }),
      newHuntResult({
        clientId: 'C.5678',
        payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
        payload: readLowLevelFlowResult,
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(2);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
    expect(await clientIds[1].text()).toContain('Client ID: C.5678');
  }));
});
