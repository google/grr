import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {OutputPluginLogEntryType} from '../../../lib/models/flow';
import {FlowStore} from '../../../store/flow_store';
import {FlowStoreMock, newFlowStoreMock} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FlowOutputPluginLogs} from './flow_output_plugin_logs';
import {FlowOutputPluginLogsHarness} from './testing/flow_output_plugin_logs_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FlowOutputPluginLogs);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowOutputPluginLogsHarness,
  );
  return {fixture, harness};
}

describe('Flow Output Plugin Logs Component', () => {
  let flowStoreMock: FlowStoreMock;

  beforeEach(waitForAsync(() => {
    flowStoreMock = newFlowStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowOutputPluginLogs, NoopAnimationsModule],
      providers: [{provide: FlowStore, useValue: flowStoreMock}],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('can be created with no rows', fakeAsync(async () => {
    flowStoreMock.outputPluginLogs = signal([]);
    const {harness} = await createComponent();
    expect(await harness.getRows()).toHaveSize(0);
  }));

  it('shows a single row', fakeAsync(async () => {
    flowStoreMock.outputPluginLogs = signal([
      {
        outputPluginId: 'plugin1',
        logEntryType: OutputPluginLogEntryType.LOG,
        timestamp: new Date('2023-12-11T12:18:26.152Z'),
        message: 'log message',
      },
    ]);
    const {harness} = await createComponent();
    expect(await harness.getRows()).toHaveSize(1);

    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2023-12-11 12:18:26 UTC',
    );
    expect(await harness.getCellText(0, 'outputPluginId')).toBe('plugin1');
    expect(await harness.getCellText(0, 'logEntryType')).toBe('LOG');
    expect(await harness.getCellText(0, 'message')).toBe('log message');
  }));

  it('shows multiple rows of different types', fakeAsync(async () => {
    flowStoreMock.outputPluginLogs = signal([
      {
        outputPluginId: 'plugin1',
        logEntryType: OutputPluginLogEntryType.LOG,
        timestamp: new Date('2023-12-11T12:18:26.152Z'),
        message: 'log message',
      },
      {
        outputPluginId: 'plugin2',
        logEntryType: OutputPluginLogEntryType.ERROR,
        timestamp: new Date('2023-12-11T12:18:26.152Z'),
        message: 'error message',
      },
    ]);
    const {harness} = await createComponent();
    expect(await harness.getRows()).toHaveSize(2);

    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2023-12-11 12:18:26 UTC',
    );
    expect(await harness.getCellText(0, 'outputPluginId')).toBe('plugin1');
    expect(await harness.getCellText(0, 'logEntryType')).toBe('LOG');
    expect(await harness.getCellText(0, 'message')).toBe('log message');

    expect(await harness.getCellText(1, 'timestamp')).toContain(
      '2023-12-11 12:18:26 UTC',
    );
    expect(await harness.getCellText(1, 'outputPluginId')).toBe('plugin2');
    expect(await harness.getCellText(1, 'logEntryType')).toBe('ERROR');
    expect(await harness.getCellText(1, 'message')).toBe('error message');
  }));

  it('initializes table with no sort order', fakeAsync(async () => {
    flowStoreMock.outputPluginLogs = signal([
      {
        timestamp: new Date(2),
        outputPluginId: 'plugin2',
      },
      {
        timestamp: new Date(3),
        outputPluginId: 'plugin3',
      },
      {
        timestamp: new Date(1),
        outputPluginId: 'plugin1',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const timestampHeader = await sort.getSortHeaders({label: 'Timestamp'});
    expect(await timestampHeader[0].getSortDirection()).toBe('');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'outputPluginId')).toContain('plugin2');
    expect(await harness.getCellText(1, 'outputPluginId')).toContain('plugin3');
    expect(await harness.getCellText(2, 'outputPluginId')).toContain('plugin1');
  }));

  it('can sort timestamp column in ascending order', fakeAsync(async () => {
    flowStoreMock.outputPluginLogs = signal([
      {
        timestamp: new Date(2),
        outputPluginId: 'plugin2',
      },
      {
        timestamp: new Date(3),
        outputPluginId: 'plugin3',
      },
      {
        timestamp: new Date(1),
        outputPluginId: 'plugin1',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const timestampHeader = await sort.getSortHeaders({label: 'Timestamp'});
    await timestampHeader[0].click();

    expect(await timestampHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'outputPluginId')).toContain('plugin1');
    expect(await harness.getCellText(1, 'outputPluginId')).toContain('plugin2');
    expect(await harness.getCellText(2, 'outputPluginId')).toContain('plugin3');
  }));
});
