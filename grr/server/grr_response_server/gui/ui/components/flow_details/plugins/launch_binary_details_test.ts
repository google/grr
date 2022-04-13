import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {LaunchBinaryArgs} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {LaunchBinaryDetails} from './launch_binary_details';
import {PluginsModule} from './module';


initTestEnvironment();

describe('LaunchBinaryDetails component', () => {
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

  it('shows binary path as result accordion title', () => {
    const args: LaunchBinaryArgs = {binary: '/foo/bar'};
    const fixture = TestBed.createComponent(LaunchBinaryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'LaunchBinary',
      args,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo/bar');
  });

  it('displays results', async () => {
    const args: LaunchBinaryArgs = {binary: '/foo/bar'};
    const fixture = TestBed.createComponent(LaunchBinaryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'LaunchBinary',
      args,
      state: FlowState.FINISHED,
      resultCounts: [{type: 'LaunchBinaryResult', count: 1}],
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'LaunchBinaryResult',
      payload: {
        stdout: btoa('resulttext\nlinetwo\n'),
        stderr: btoa('errortext\nerrortwo\n'),
      },
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('resulttext\nlinetwo');
    expect(fixture.nativeElement.innerText).toContain('errortext\nerrortwo');
  });
});
