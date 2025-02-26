import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {
  FlowResultsLocalStoreMock,
  mockFlowResultsLocalStore,
} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';
import {ListProcessesDetails} from './list_processes_details';
import {PluginsModule} from './module';

initTestEnvironment();

describe('ListProcessesDetails component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, PluginsModule],
      providers: [],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(FlowResultsLocalStore, {
        useFactory: () => flowResultsLocalStore,
      })
      .compileComponents();
  }));

  it('displays process view', async () => {
    const fixture = TestBed.createComponent(ListProcessesDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness = await harnessLoader.getHarness(
      ResultAccordionHarness,
    );
    await resultAccordionHarness.toggle();
    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'Process',
        payload: {pid: 0, cmdline: ['/foo', 'bar']},
      }),
    ]);
    fixture.detectChanges();

    expect(
      fixture.nativeElement.querySelector('app-process-view'),
    ).toBeDefined();
    // Verify that the process view is not empty.
    expect(
      fixture.nativeElement.querySelector('app-process-view').children.length,
    ).toBe(1);
    expect(
      fixture.nativeElement.querySelector('app-process-view').children[0]
        .innerText,
    ).toContain('/foo');
  });
});
