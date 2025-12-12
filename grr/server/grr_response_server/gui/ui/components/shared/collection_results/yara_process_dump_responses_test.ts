import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {YaraProcessDumpResponse as ApiYaraProcessDumpResponse} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {YaraProcessDumpResponsesHarness} from './testing/yara_process_dump_responses_harness';
import {YaraProcessDumpResponses} from './yara_process_dump_responses';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(YaraProcessDumpResponses);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    YaraProcessDumpResponsesHarness,
  );

  return {fixture, harness};
}

describe('Yara Process Dump Responses Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [YaraProcessDumpResponses, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no table if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.table()).toBeNull();
  }));

  it('shows a single scan match', fakeAsync(async () => {
    const yaraProcessDumpResponse: ApiYaraProcessDumpResponse = {
      dumpedProcesses: [
        {
          error: 'Error',
          process: {
            pid: 123,
            cmdline: ['foo', 'bar'],
          },
          memoryRegions: [{}, {}, {}],
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: yaraProcessDumpResponse,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(0, 'cmdline')).toContain('foo bar');
    expect(await harness.getCellText(0, 'memoryRegionsCount')).toContain('3');
    expect(await harness.getCellText(0, 'error')).toContain('Error');
  }));

  it('shows unnested results', fakeAsync(async () => {
    const yaraProcessDumpResponse: ApiYaraProcessDumpResponse = {
      dumpedProcesses: [
        {
          error: 'Error1',
          process: {
            pid: 111,
            cmdline: ['foo2', 'bar3'],
          },
          memoryRegions: [{}],
        },
        {
          process: {
            pid: 222,
            cmdline: ['foo2', 'bar2'],
          },
          memoryRegions: [{}, {}],
        },
      ],
      errors: [
        {
          process: {
            pid: 333,
            cmdline: ['foo3', 'bar3'],
          },
          error: 'Error3',
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: yaraProcessDumpResponse,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'pid')).toEqual('111');
    expect(await harness.getCellText(0, 'cmdline')).toContain('foo2 bar3');
    expect(await harness.getCellText(0, 'memoryRegionsCount')).toContain('1');
    expect(await harness.getCellText(0, 'error')).toContain('Error1');

    expect(await harness.getCellText(1, 'pid')).toEqual('222');
    expect(await harness.getCellText(1, 'cmdline')).toContain('foo2 bar2');
    expect(await harness.getCellText(1, 'memoryRegionsCount')).toContain('2');

    expect(await harness.getCellText(2, 'pid')).toEqual('333');
    expect(await harness.getCellText(2, 'cmdline')).toContain('foo3 bar3');
    expect(await harness.getCellText(2, 'memoryRegionsCount')).toContain('0');
    expect(await harness.getCellText(2, 'error')).toContain('Error3');
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    function createYaraProcessDumpResponse(
      pid: number,
    ): ApiYaraProcessDumpResponse {
      return {
        dumpedProcesses: [
          {
            process: {
              pid,
              cmdline: ['foo', 'bar'],
            },
            memoryRegions: [{}, {}, {}],
          },
        ],
      };
    }

    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: createYaraProcessDumpResponse(123),
      }),
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: createYaraProcessDumpResponse(234),
      }),
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: createYaraProcessDumpResponse(345),
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(1, 'pid')).toEqual('234');
    expect(await harness.getCellText(2, 'pid')).toEqual('345');
  }));

  it('shows client id column for hunt results', fakeAsync(async () => {
    const yaraProcessDumpResponse: ApiYaraProcessDumpResponse = {
      dumpedProcesses: [
        {
          process: {
            pid: 123,
            cmdline: ['foo', 'bar'],
          },
          memoryRegions: [{}, {}, {}],
        },
      ],
    };
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: yaraProcessDumpResponse,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));
});
