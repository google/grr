import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ExecuteResponse as ApiExecuteResponse} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ExecuteResponseResults} from './execute_response_results';
import {ExecuteResponseResultsHarness} from './testing/execute_response_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ExecuteResponseResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExecuteResponseResultsHarness,
  );

  return {fixture, harness};
}

describe('Execute Response Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ExecuteResponseResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows a single result', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_RESPONSE,
        payload: {
          request: {
            cmd: 'cmd',
            args: ['arg1', 'arg2'],
            timeLimit: 123,
          },
          exitStatus: 1,
          stdout: btoa('stdout'),
          stderr: btoa('stderr'),
          timeUsed: 123,
        } as ApiExecuteResponse,
      }),
    ]);

    expect(await harness.results()).toHaveSize(1);
    const cmd = await harness.getCmd(0);
    expect(await cmd.text()).toBe('cmd arg1 arg2');
    const exitStatus = await harness.getExitStatus(0);
    expect(await exitStatus.text()).toBe('1');
    const stdout = await harness.getStdout(0);
    expect(await stdout.text()).toBe('stdout');
    const stderr = await harness.getStderr(0);
    expect(await stderr!.text()).toBe('stderr');
  });

  it('shows multiple results', async () => {
    const payload: ApiExecuteResponse = {
      request: {
        cmd: 'cmd',
        args: ['arg1', 'arg2'],
        timeLimit: 123,
      },
      exitStatus: 1,
      stdout: btoa('stdout'),
      stderr: btoa('stderr'),
      timeUsed: 123,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_RESPONSE,
        payload,
      }),
      newFlowResult({
        payloadType: PayloadType.EXECUTE_RESPONSE,
        payload,
      }),
    ]);

    expect(await harness.results()).toHaveSize(2);
  });

  it('shows a result with no stderr', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.EXECUTE_RESPONSE,
        payload: {
          request: {
            cmd: 'cmd',
            args: ['arg1', 'arg2'],
            timeLimit: 123,
          },
          exitStatus: 0,
          stdout: btoa('stdout'),
          timeUsed: 123,
        } as ApiExecuteResponse,
      }),
    ]);

    expect(await harness.results()).toHaveSize(1);
    const cmd = await harness.getCmd(0);
    expect(await cmd.text()).toBe('cmd arg1 arg2');
    const exitStatus = await harness.getExitStatus(0);
    expect(await exitStatus.text()).toBe('0');
    const stdout = await harness.getStdout(0);
    expect(await stdout.text()).toBe('stdout');
    const stderr = await harness.getStderr(0);
    expect(stderr).toBeNull();
  });

  it('shows client id for hunt results', async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payload: {
          request: 'hello_world',
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
          request: 'hello_world',
        },
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(0);
  });
});
