import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResult} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {NetstatArgs, NetworkConnectionFamily, NetworkConnectionState, NetworkConnectionType} from '../../../lib/api/api_interfaces';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {PluginsModule} from './module';

import {NetstatDetails} from './netstat_details';


initTestEnvironment();

describe('NetstatDetails component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],

          providers: []
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('title: displays `Listening only` when set in args', () => {
    const args: NetstatArgs = {listeningOnly: true};
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Listening only');
  });

  it('title: displays `All connections` when listeningOnly is not set in args',
     () => {
       const args: NetstatArgs = {listeningOnly: false};
       const fixture = TestBed.createComponent(NetstatDetails);
       fixture.componentInstance.flow = newFlow({
         state: FlowState.FINISHED,
         args,
       });
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('All connections');
     });

  it('displays netstat results', async () => {
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'NetworkConnection',
      payload: {
        pid: 1234,
        processName: 'foo',
        state: NetworkConnectionState.LISTEN,
        type: NetworkConnectionType.SOCK_DGRAM,
        family: NetworkConnectionFamily.INET6,
        localAddress: {
          ip: 'some:local:ip',
          port: 42,
        },
        remoteAddress: {
          ip: 'some:remote:ip',
          port: 13,
        },
      }
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('1234');
    expect(fixture.nativeElement.innerText).toContain('foo');
    expect(fixture.nativeElement.innerText).toContain('LISTEN');
    expect(fixture.nativeElement.innerText).toContain('UDP');
    expect(fixture.nativeElement.innerText).toContain('IPv6');
    expect(fixture.nativeElement.innerText).toContain('some:local:ip');
    expect(fixture.nativeElement.innerText).toContain('42');
    expect(fixture.nativeElement.innerText).toContain('some:remote:ip');
    expect(fixture.nativeElement.innerText).toContain('13');
  });
});
