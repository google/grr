import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {By} from '@angular/platform-browser';

import {NetstatArgs, NetworkConnectionFamily, NetworkConnectionState, NetworkConnectionType} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
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
          providers: [],
          teardown: {destroyAfterEach: false}
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
      }),
      ...generateResults(9),
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
    expect(fixture.nativeElement.innerText).toContain('No data');

    // Filter is cleared, all rows are showed again.
    filterInput.nativeElement.value = '';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('1234');
    expect(fixture.nativeElement.innerText).toContain('5678');
  });

  it('sorts results', async () => {
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
          processName: 'foo',
        }
      }),
      newFlowResult({
        payloadType: 'NetworkConnection',
        payload: {
          processName: 'bar',
        }
      })
    ]);
    fixture.detectChanges();

    function getProcessNames() {
      const p1 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(1) td:nth-child(2)'));
      const p2 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(2) td:nth-child(2)'));
      return [p1.nativeElement.innerText, p2.nativeElement.innerText];
    }

    expect(getProcessNames()).toEqual([
      jasmine.stringMatching('foo'), jasmine.stringMatching('bar')
    ]);

    // Sort by processName.
    const sort = await harnessLoader.getHarness(MatSortHarness);
    const headers = await sort.getSortHeaders({sortDirection: ''});
    await headers[1].click();

    expect(getProcessNames()).toEqual([
      jasmine.stringMatching('bar'), jasmine.stringMatching('foo')
    ]);
  });

  it('default pagination works', async () => {
    const fixture = TestBed.createComponent(NetstatDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next(generateResults(200));
    fixture.detectChanges();

    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    // Paginators start with default values, process0-9 are shown, but 10 isn't.
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(fixture.nativeElement.innerText).toContain('process0');
    expect(fixture.nativeElement.innerText).toContain('process9');
    expect(fixture.nativeElement.innerText).not.toContain('process10');
  });

  it('clicking TOP paginator updates bottom paginator state (page size)',
     async () => {
       const fixture = TestBed.createComponent(NetstatDetails);
       fixture.componentInstance.flow = newFlow({
         state: FlowState.FINISHED,
         args: {},
       });

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const resultAccordionHarness =
           await harnessLoader.getHarness(ResultAccordionHarness);
       await resultAccordionHarness.toggle();

       flowResultsLocalStore.mockedObservables.results$.next(
           generateResults(200));
       fixture.detectChanges();
       const paginatorTop = await harnessLoader.getHarness(

           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on top paginator should update the bottom paginator.
       await paginatorTop.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 200');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 200');
       expect(fixture.nativeElement.innerText).toContain('process0');
       expect(fixture.nativeElement.innerText).toContain('process49');
     });

  it('clicking BOTTOM paginator updates top paginator state (page size)',
     async () => {
       const fixture = TestBed.createComponent(NetstatDetails);
       fixture.componentInstance.flow = newFlow({
         state: FlowState.FINISHED,
         args: {},
       });

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const resultAccordionHarness =
           await harnessLoader.getHarness(ResultAccordionHarness);
       await resultAccordionHarness.toggle();

       flowResultsLocalStore.mockedObservables.results$.next(
           generateResults(200));
       fixture.detectChanges();
       const paginatorTop = await harnessLoader.getHarness(

           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on bottom paginator should update the top paginator.
       await paginatorBottom.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 200');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 200');
       expect(fixture.nativeElement.innerText).toContain('process0');
       expect(fixture.nativeElement.innerText).toContain('process49');
     });
});

function generateResult(n: number) {
  return newFlowResult({
    payloadType: 'NetworkConnection',
    payload: {
      pid: n,
      processName: `process${n}`,
    }
  });
}

function generateResults(count: number) {
  return [...Array.from({length: count}).keys()].map(generateResult);
}
