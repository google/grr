import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ExecutePythonHackResult as ApiExecutePythonHackResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ExecutePythonHackResults} from './execute_python_hack_results';
import {ExecutePythonHackResultsHarness} from './testing/execute_python_hack_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ExecutePythonHackResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExecutePythonHackResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Multiple Files Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ExecutePythonHackResults, NoopAnimationsModule],
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

  it('shows a python hack result', fakeAsync(async () => {
    const executePythonHackResult: ApiExecutePythonHackResult = {
      resultString: 'line1\nline2',
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_PYTHON_HACK_RESULT,
        payload: executePythonHackResult,
      }),
    ]);

    const codeblocks = await harness.codeblocks();
    expect(codeblocks).toHaveSize(1);
    const codeLines = await codeblocks[0].linesText();
    expect(codeLines).toHaveSize(2);
    expect(codeLines).toEqual(['line1', 'line2']);
  }));

  it('shows multiple python hack results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_PYTHON_HACK_RESULT,
        payload: {resultString: 'line1\nline2'},
      }),
      newFlowResult({
        payloadType: PayloadType.EXECUTE_PYTHON_HACK_RESULT,
        payload: {resultString: 'line3'},
      }),
      newFlowResult({
        payloadType: PayloadType.EXECUTE_PYTHON_HACK_RESULT,
        payload: {},
      }),
    ]);

    const codeblocks = await harness.codeblocks();
    expect(codeblocks).toHaveSize(3);
    expect(await codeblocks[0].linesText()).toEqual(['line1', 'line2']);
    expect(await codeblocks[1].linesText()).toEqual(['line3']);
    expect(await codeblocks[2].linesText()).toEqual([]);
  }));

  it('shows client id for hunt results', fakeAsync(async () => {
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
  }));

  it('does not show client id for flow results', fakeAsync(async () => {
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
  }));
});
