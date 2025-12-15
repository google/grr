import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {YaraProcessScanMatch as ApiYaraProcessScanMatch} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {YaraProcessScanMatchesHarness} from './testing/yara_process_scan_matches_harness';
import {YaraProcessScanMatches} from './yara_process_scan_matches';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(YaraProcessScanMatches);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    YaraProcessScanMatchesHarness,
  );

  return {fixture, harness};
}

describe('Yara Process Scan Matches Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [YaraProcessScanMatches, NoopAnimationsModule],
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
    const yaraProcessScanMatch: ApiYaraProcessScanMatch = {
      process: {
        pid: 123,
        name: 'process',
      },
      match: [
        {
          ruleName: 'FooBar',
          stringMatches: [
            {
              data: btoa('ExampleData'),
              stringId: 'StringId',
              offset: '456',
              context: btoa('ExampleContext'),
            },
          ],
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: yaraProcessScanMatch,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(0, 'process')).toContain('process');
    expect(await harness.getCellText(0, 'ruleId')).toContain('FooBar');
    expect(await harness.getCellText(0, 'matchOffset')).toContain('456');
    expect(await harness.getCellText(0, 'matchId')).toContain('StringId');
    expect(await harness.getCellText(0, 'matchData')).toContain('ExampleData');
    expect(await harness.getCellText(0, 'context')).toContain('Context');
  }));

  it('shows unnested results', fakeAsync(async () => {
    const yaraProcessScanMatch: ApiYaraProcessScanMatch = {
      process: {
        pid: 123,
        name: 'process123',
      },
      match: [
        {
          ruleName: 'FooBar1',
          stringMatches: [
            {
              data: btoa('ExampleData1'),
              stringId: 'StringId1',
              offset: '111',
              context: btoa('Context1'),
            },
          ],
        },
        {
          ruleName: 'FooBar23',
          stringMatches: [
            {
              data: btoa('ExampleData2'),
              stringId: 'StringId2',
              offset: '222',
              context: btoa('Context2'),
            },
            {
              data: btoa('ExampleData3'),
              stringId: 'StringId3',
              offset: '333',
              context: btoa('Context3'),
            },
          ],
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: yaraProcessScanMatch,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(0, 'process')).toContain('process123');
    expect(await harness.getCellText(0, 'ruleId')).toContain('FooBar1');
    expect(await harness.getCellText(0, 'matchOffset')).toContain('111');
    expect(await harness.getCellText(0, 'matchId')).toContain('StringId1');
    expect(await harness.getCellText(0, 'matchData')).toContain('ExampleData1');
    expect(await harness.getCellText(0, 'context')).toContain('Context1');

    expect(await harness.getCellText(1, 'pid')).toEqual('123');
    expect(await harness.getCellText(1, 'process')).toContain('process123');
    expect(await harness.getCellText(1, 'ruleId')).toContain('FooBar23');
    expect(await harness.getCellText(1, 'matchOffset')).toContain('222');
    expect(await harness.getCellText(1, 'matchId')).toContain('StringId2');
    expect(await harness.getCellText(1, 'matchData')).toContain('ExampleData2');
    expect(await harness.getCellText(1, 'context')).toContain('Context2');

    expect(await harness.getCellText(2, 'pid')).toEqual('123');
    expect(await harness.getCellText(2, 'process')).toContain('process123');
    expect(await harness.getCellText(2, 'ruleId')).toContain('FooBar23');
    expect(await harness.getCellText(2, 'matchOffset')).toContain('333');
    expect(await harness.getCellText(2, 'matchId')).toContain('StringId3');
    expect(await harness.getCellText(2, 'matchData')).toContain('ExampleData3');
    expect(await harness.getCellText(2, 'context')).toContain('Context3');
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    function createYaraProcessScanMatch(pid: number): ApiYaraProcessScanMatch {
      return {
        process: {
          pid,
          name: `process-${pid}`,
        },
        match: [
          {
            ruleName: 'FooBar1',
            stringMatches: [
              {
                data: btoa('ExampleData'),
                stringId: 'StringId',
                offset: '0',
                context: btoa('Context'),
              },
            ],
          },
        ],
      };
    }

    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: createYaraProcessScanMatch(123),
      }),
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: createYaraProcessScanMatch(234),
      }),
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: createYaraProcessScanMatch(345),
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
    const yaraProcessScanMatch: ApiYaraProcessScanMatch = {
      process: {
        pid: 123,
        name: 'process',
      },
      match: [
        {
          ruleName: 'FooBar1',
          stringMatches: [
            {
              data: btoa('ExampleData'),
              stringId: 'StringId',
              offset: '0',
              context: btoa('Context'),
            },
          ],
        },
      ],
    };
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
        payload: yaraProcessScanMatch,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));
});
