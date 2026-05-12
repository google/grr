import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ExecuteBinaryResponse as ApiExecuteBinaryResponse} from '../../../lib/api/api_interfaces';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ExecuteBinaryResponses} from './execute_binary_responses';
import {ExecuteBinaryResponsesHarness} from './testing/execute_binary_responses_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ExecuteBinaryResponses);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExecuteBinaryResponsesHarness,
  );

  return {fixture, harness};
}

describe('Execute Binary Responses Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ExecuteBinaryResponses, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no codeblocks if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.codeblocks()).toHaveSize(0);
  }));

  it('shows a full binary hack responses', fakeAsync(async () => {
    const executeBinaryResponse: ApiExecuteBinaryResponse = {
      exitStatus: 1,
      stdout: btoa('stdout\nline two'),
      stderr: btoa('stderr'),
      timeUsed: 1e6,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_BINARY_RESPONSE,
        payload: executeBinaryResponse,
      }),
    ]);

    const codeblocks = await harness.codeblocks();
    expect(codeblocks).toHaveSize(3);
    expect(await codeblocks[0].linesText()).toEqual(['Exit code: 1']);
    expect(await codeblocks[1].linesText()).toEqual(['stderr']);
    expect(await codeblocks[2].linesText()).toEqual(['stdout', 'line two']);
  }));

  it('shows multiple binary hack responses', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_BINARY_RESPONSE,
        payload: {exitStatus: 1},
      }),
      newFlowResult({
        payloadType: PayloadType.EXECUTE_BINARY_RESPONSE,
        payload: {exitStatus: 2},
      }),
      newFlowResult({
        payloadType: PayloadType.EXECUTE_BINARY_RESPONSE,
        payload: {exitStatus: 3},
      }),
    ]);

    const codeblocks = await harness.codeblocks();
    expect(codeblocks).toHaveSize(3);
    expect(await codeblocks[0].linesText()).toEqual(['Exit code: 1']);
    expect(await codeblocks[1].linesText()).toEqual(['Exit code: 2']);
    expect(await codeblocks[2].linesText()).toEqual(['Exit code: 3']);
  }));
});
