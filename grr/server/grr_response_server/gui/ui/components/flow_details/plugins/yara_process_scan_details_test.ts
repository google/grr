import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {YaraProcessScanMatch} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {PluginsModule} from './module';
import {YaraProcessScanDetails} from './yara_process_scan_details';


initTestEnvironment();


describe('app-yara-process-scan-details component', () => {
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
    const fixture = TestBed.createComponent(YaraProcessScanDetails);
    expect(fixture.componentInstance.getResultDescription(newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts: [{count: 2, type: 'YaraProcessScanMatch'}]
    }))).toEqual('2 processes');
  });

  it('displays process results ', async () => {
    const fixture = TestBed.createComponent(YaraProcessScanDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {},
      resultCounts: [
        {count: 1, type: 'YaraProcessScanMatch'},
      ]
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    const payload: YaraProcessScanMatch = {
      process: {
        pid: 123,
        name: 'exampleprocess',
      },
      match: [{
        ruleName: 'ExampleRuleName',
        stringMatches: [{
          data: encodeStringToBase64('ExampleData'),
          stringId: 'ExampleStringId',
          offset: '456',
        }]
      }]
    };

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'YaraProcessScanMatch',
      payload,
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('123');
    expect(fixture.nativeElement.textContent).toContain('exampleprocess');
    expect(fixture.nativeElement.textContent).toContain('ExampleRuleName');
    expect(fixture.nativeElement.textContent).toContain('ExampleData');
    expect(fixture.nativeElement.textContent).toContain('ExampleStringId');
  });
});
