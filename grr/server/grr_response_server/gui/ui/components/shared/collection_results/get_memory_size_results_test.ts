import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {GetMemorySizeResult as ApiGetMemorySizeResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {GetMemorySizeResults} from './get_memory_size_results';
import {GetMemorySizeResultsHarness} from './testing/get_memory_size_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(GetMemorySizeResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    GetMemorySizeResultsHarness,
  );

  return {fixture, harness};
}

describe('Get Memory Size Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [GetMemorySizeResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows a single memory size', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.GET_MEMORY_SIZE_RESULT,
        payload: {
          totalBytes: '123',
        } as ApiGetMemorySizeResult,
      }),
    ]);

    const memorySizes = await harness.memorySize();
    expect(memorySizes).toHaveSize(1);
    expect(await memorySizes[0].text()).toContain('123 B');
  }));

  it('shows multiple memory sizes', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.GET_MEMORY_SIZE_RESULT,
        payload: {} as ApiGetMemorySizeResult,
      }),
      newFlowResult({
        payloadType: PayloadType.GET_MEMORY_SIZE_RESULT,
        payload: {} as ApiGetMemorySizeResult,
      }),
    ]);

    const memorySizes = await harness.memorySize();
    expect(memorySizes).toHaveSize(2);
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
