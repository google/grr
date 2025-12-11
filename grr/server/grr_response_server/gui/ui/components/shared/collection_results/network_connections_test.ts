import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  NetworkConnection as ApiNetworkConnection,
  NetworkConnectionFamily,
  NetworkConnectionState,
  NetworkConnectionType,
} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {NetworkConnections} from './network_connections';
import {NetworkConnectionsHarness} from './testing/network_connections_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(NetworkConnections);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    NetworkConnectionsHarness,
  );

  return {fixture, harness};
}

describe('Network Connections Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NetworkConnections, NoopAnimationsModule],
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

  it('shows a single network connection', fakeAsync(async () => {
    const networkConnection: ApiNetworkConnection = {
      family: NetworkConnectionFamily.INET,
      type: NetworkConnectionType.SOCK_STREAM,
      localAddress: {
        ip: '127.0.0.1',
        port: 1234,
      },
      remoteAddress: {
        ip: '192.168.0.1',
        port: 4321,
      },
      state: NetworkConnectionState.ESTABLISHED,
      pid: 123,
      processName: 'foo',
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.NETWORK_CONNECTION,
        payload: networkConnection,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(0, 'processName')).toContain('foo');
    expect(await harness.getCellText(0, 'state')).toContain('ESTABLISHED');
    expect(await harness.getCellText(0, 'type')).toContain('TCP');
    expect(await harness.getCellText(0, 'family')).toContain('IPv4');
    expect(await harness.getCellText(0, 'localIP')).toContain('127.0.0.1');
    expect(await harness.getCellText(0, 'localPort')).toContain('1234');
    expect(await harness.getCellText(0, 'remoteIP')).toContain('192.168.0.1');
    expect(await harness.getCellText(0, 'remotePort')).toContain('4321');
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.NETWORK_CONNECTION,
        payload: {
          pid: 123,
        },
      }),
      newFlowResult({
        payloadType: PayloadType.NETWORK_CONNECTION,
        payload: {
          pid: 234,
        },
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'pid')).toEqual('123');
    expect(await harness.getCellText(1, 'pid')).toEqual('234');
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

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  });
});
