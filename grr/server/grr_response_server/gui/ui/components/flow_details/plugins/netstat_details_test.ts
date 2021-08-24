import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
// import {MatInput} from '@angular/material/input';
import {By} from '@angular/platform-browser';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResult} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {FlowResultCount, NetstatArgs, NetworkConnectionFamily, NetworkConnectionState, NetworkConnectionType} from '../../../lib/api/api_interfaces';
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

  it('does NOT display progress when flow is not finished', () => {
    const resultCounts: ReadonlyArray<FlowResultCount> =
        [{type: 'NetworkConnection', count: 1}];
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.RUNNING,
      args: {},
      resultCounts,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('1 connection');
  });

  it('displays progress based on flow metadata (single connection)', () => {
    const resultCounts: ReadonlyArray<FlowResultCount> =
        [{type: 'NetworkConnection', count: 1}];
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('1 connection');
  });

  it('displays progress based on flow metadata (multiple connections)', () => {
    const resultCounts: ReadonlyArray<FlowResultCount> =
        [{type: 'NetworkConnection', count: 42}];
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('42 connections');
  });

  it('does NOT display download button when flow is NOT finished', () => {
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.RUNNING,
      args: {},
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Download');
  });

  it('displays download button when flow is finished', () => {
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Download');
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

  it('filters netstat results', async () => {
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'NetworkConnection',
        payload: {
          pid: 1234,
          processName: 'foo',
          state: NetworkConnectionState.LISTEN,
          type: NetworkConnectionType.SOCK_DGRAM,
          family: NetworkConnectionFamily.INET6,
          localAddress: {
            ip: 'local:ip:1',
            port: 42,
          },
          remoteAddress: {
            ip: 'remote:ip:1',
            port: 13,
          },
        }
      }),
      newFlowResult({
        payloadType: 'NetworkConnection',
        payload: {
          pid: 5678,
          processName: 'bar',
          state: NetworkConnectionState.ESTABLISHED,
          type: NetworkConnectionType.SOCK_STREAM,
          family: NetworkConnectionFamily.INET,
          localAddress: {
            ip: 'local:ip:2',
            port: 42,
          },
          remoteAddress: {
            ip: 'remote:ip:2',
            port: 13,
          },
        }
      })
    ]);
    fixture.detectChanges();

    // Table starts with both rows displayed.
    expect(fixture.nativeElement.innerText).toContain('1234');
    expect(fixture.nativeElement.innerText).toContain('5678');

    const filterInput = fixture.debugElement.query(By.css('input'));

    // Filter is applied, selecting only the first row by process name.
    filterInput.nativeElement.value = 'foo';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('1234');
    expect(fixture.nativeElement.innerText).not.toContain('5678');

    // Filter is applied, selecting only the second row by ip address.
    filterInput.nativeElement.value = 'bar';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('1234');
    expect(fixture.nativeElement.innerText).toContain('5678');

    // Filter is applied, selects no row.
    filterInput.nativeElement.value = 'invalid';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('1234');
    expect(fixture.nativeElement.innerText).not.toContain('5678');
    expect(fixture.nativeElement.innerText)
        .toContain('No data matching the filter "invalid"');

    // Filter is cleared, all rows are showed again.
    filterInput.nativeElement.value = '';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('1234');
    expect(fixture.nativeElement.innerText).toContain('5678');
  });
});
