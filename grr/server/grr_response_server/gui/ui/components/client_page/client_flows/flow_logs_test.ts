

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowStore} from '../../../store/flow_store';
import {FlowStoreMock, newFlowStoreMock} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FlowLogs} from './flow_logs';
import {FlowLogsHarness} from './testing/flow_logs_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FlowLogs);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowLogsHarness,
  );
  return {fixture, harness};
}

describe('Flow Logs Component', () => {
  let flowStoreMock: FlowStoreMock;

  beforeEach(waitForAsync(() => {
    flowStoreMock = newFlowStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowLogs, NoopAnimationsModule],
      providers: [{provide: FlowStore, useValue: flowStoreMock}],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeDefined();
  });

  it('can be created with no rows', fakeAsync(async () => {
    flowStoreMock.logs = signal([]);
    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(0);
  }));

  it('shows a single row', fakeAsync(async () => {
    flowStoreMock.logs = signal([
      {
        timestamp: new Date(1571789996681),
        logMessage: 'log message',
      },
    ]);
    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2019-10-23 00:19:56 UTC',
    );
    expect(await harness.getCellText(0, 'logMessage')).toBe('log message');
  }));

  it('shows a single row with multiline log message', fakeAsync(async () => {
    flowStoreMock.logs = signal([
      {
        timestamp: new Date(1571789996681),
        logMessage: 'first line\\nsecond line',
      },
    ]);
    const {harness} = await createComponent();

    expect(await harness.getCellText(0, 'logMessage')).toContain('first line');
    expect(await harness.getCellText(0, 'logMessage')).toContain('second line');
  }));

  it('can show several rows', fakeAsync(async () => {
    flowStoreMock.logs = signal([
      {
        timestamp: new Date(1571789996681),
        logMessage: 'first log',
      },
      {
        timestamp: new Date(1571789996682),
        logMessage: 'second log',
      },
      {
        timestamp: new Date(1571789996683),
        logMessage: 'third log',
      },
    ]);

    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'logMessage')).toContain('first log');
    expect(await harness.getCellText(1, 'logMessage')).toContain('second log');
    expect(await harness.getCellText(2, 'logMessage')).toContain('third log');
  }));

  it('initializes table with no sort order', fakeAsync(async () => {
    flowStoreMock.logs = signal([
      {
        timestamp: new Date(2),
        logMessage: 'log 2',
      },
      {
        timestamp: new Date(3),
        logMessage: 'log 3',
      },
      {
        timestamp: new Date(1),
        logMessage: 'log 1',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const timestampHeader = await sort.getSortHeaders({label: 'Timestamp'});
    expect(await timestampHeader[0].getSortDirection()).toBe('');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'logMessage')).toContain('log 2');
    expect(await harness.getCellText(1, 'logMessage')).toContain('log 3');
    expect(await harness.getCellText(2, 'logMessage')).toContain('log 1');
  }));

  it('can sort timestamp column in ascending order', fakeAsync(async () => {
    flowStoreMock.logs = signal([
      {
        timestamp: new Date(2),
        logMessage: 'log 2',
      },
      {
        timestamp: new Date(3),
        logMessage: 'log 3',
      },
      {
        timestamp: new Date(1),
        logMessage: 'log 1',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const pathHeader = await sort.getSortHeaders({label: 'Timestamp'});
    await pathHeader[0].click();

    expect(await pathHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'logMessage')).toContain('log 1');
    expect(await harness.getCellText(1, 'logMessage')).toContain('log 2');
    expect(await harness.getCellText(2, 'logMessage')).toContain('log 3');
  }));
});
