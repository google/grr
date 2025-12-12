

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionLogs} from './fleet_collection_logs';
import {FleetCollectionLogsHarness} from './testing/fleet_collection_logs_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionLogs);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionLogsHarness,
  );
  return {fixture, harness};
}

describe('Fleet Collection Logs Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    TestBed.configureTestingModule({
      imports: [FleetCollectionLogs, NoopAnimationsModule],
      providers: [
        {provide: FleetCollectionStore, useValue: fleetCollectionStoreMock},
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('can be created with no rows', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionLogs = signal([]);
    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(0);
  }));

  it('shows a single row', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
      {
        timestamp: new Date(1571789996681),
        clientId: 'C.1234567890',
        flowId: 'F1234567890',
        logMessage: 'log message',
      },
    ]);
    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2019-10-23 00:19:56 UTC',
    );
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234567890');
    expect(await harness.getCellText(0, 'flowId')).toContain('F1234567890');
    expect(await harness.getCellText(0, 'logMessage')).toBe('log message');
  }));

  it('shows a single row with multi-line log message', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
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
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
      {
        timestamp: new Date(1571789996681),
        clientId: 'C.1234567890',
        flowId: 'F1234567890',
        logMessage: 'first log',
      },
      {
        timestamp: new Date(1571789996682),
        clientId: 'C.1234567891',
        flowId: 'F1234567891',
        logMessage: 'second log',
      },
      {
        timestamp: new Date(1571789996683),
        clientId: 'C.1234567892',
        flowId: 'F1234567892',
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
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
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
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
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

  it('can sort client id column in ascending order', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
      {
        timestamp: new Date(1),
        clientId: 'C.11111111',
        flowId: 'F1234567890',
        logMessage: 'log 1',
      },
      {
        timestamp: new Date(2),
        clientId: 'C.00000000',
        flowId: 'F1234567891',
        logMessage: 'log 0',
      },
      {
        timestamp: new Date(3),
        clientId: 'C.22222222',
        flowId: 'F1234567892',
        logMessage: 'log 2',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const clientIdHeader = await sort.getSortHeaders({label: 'Client ID'});
    await clientIdHeader[0].click();

    expect(await clientIdHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.00000000');
    expect(await harness.getCellText(1, 'clientId')).toContain('C.11111111');
    expect(await harness.getCellText(2, 'clientId')).toContain('C.22222222');
  }));

  it('can sort flow id column in ascending order', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionLogs = signal([
      {
        timestamp: new Date(1),
        clientId: 'C.1234567890',
        flowId: 'F11111111',
        logMessage: 'log 1',
      },
      {
        timestamp: new Date(2),
        clientId: 'C.1234567891',
        flowId: 'F00000000',
        logMessage: 'log 0',
      },
      {
        timestamp: new Date(3),
        clientId: 'C.1234567892',
        flowId: 'F22222222',
        logMessage: 'log 2',
      },
    ]);
    const {harness} = await createComponent();

    const sort = await harness.sort();
    const flowIdHeader = await sort.getSortHeaders({label: 'Flow ID'});
    await flowIdHeader[0].click();

    expect(await flowIdHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'flowId')).toContain('F00000000');
    expect(await harness.getCellText(1, 'flowId')).toContain('F11111111');
    expect(await harness.getCellText(2, 'flowId')).toContain('F22222222');
  }));
});
