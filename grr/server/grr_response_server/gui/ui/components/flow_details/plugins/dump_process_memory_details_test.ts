import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {YaraProcessDumpResponse} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {DumpProcessMemoryDetails} from './dump_process_memory_details';
import {PluginsModule} from './module';


initTestEnvironment();


describe('app-dump-process-memory-details component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
            RouterTestingModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        // Override ALL providers to mock the GlobalStore that is provided by
        // each component.
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('displays result count ', async () => {
    const fixture = TestBed.createComponent(DumpProcessMemoryDetails);
    expect(fixture.componentInstance.getResultDescription(newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts: [
        {count: 1, type: 'YaraProcessDumpResponse'},
        {count: 3, type: 'StatEntry'}
      ]
    }))).toEqual('3 regions');
  });

  it('displays process results ', async () => {
    const fixture = TestBed.createComponent(DumpProcessMemoryDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts: [
        {count: 1, type: 'YaraProcessDumpResponse'},
        {count: 3, type: 'StatEntry'}
      ]
    });


    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'YaraProcessDumpResponse',
      payload: {
        dumpedProcesses: [{
          process: {
            pid: 123,
            cmdline: ['foo', 'bar'],
          },
          memoryRegions: [{}, {}, {}]
        }]
      } as YaraProcessDumpResponse,
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('123');
    expect(fixture.nativeElement.textContent).toContain('foo bar');
    expect(fixture.nativeElement.textContent).toContain('3 regions');
  });
});
