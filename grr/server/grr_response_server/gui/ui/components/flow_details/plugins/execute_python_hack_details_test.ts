import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ExecutePythonHackArgs} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {ExecutePythonHackDetails} from './execute_python_hack_details';
import {PluginsModule} from './module';


initTestEnvironment();

describe('ExecutePythonHackDetails component', () => {
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
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('shows python hack path as result accordion title', () => {
    const args: ExecutePythonHackArgs = {hackName: '/foo/bar'};
    const fixture = TestBed.createComponent(ExecutePythonHackDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'ExecutePythonHack',
      args,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo/bar');
  });

  it('displays results', async () => {
    const args: ExecutePythonHackArgs = {hackName: '/foo/bar'};
    const fixture = TestBed.createComponent(ExecutePythonHackDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'ExecutePythonHack',
      args,
      state: FlowState.FINISHED,
      resultCounts: [{type: 'ExecutePythonHackResult', count: 1}],
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'ExecutePythonHackResult',
      payload: {resultString: 'resulttext\nlinetwo\n'},
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('resulttext');
    expect(fixture.nativeElement.innerText).toContain('linetwo');
  });
});
