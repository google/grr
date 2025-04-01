import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectLargeFileFlowArgs,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {
  newCollectLargeFileFlow,
  newFlow,
  newFlowResult,
} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {
  FlowResultsLocalStoreMock,
  mockFlowResultsLocalStore,
} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {CollectLargeFileFlowDetails} from './collect_large_file_flow_details';
import {PluginsModule} from './module';

initTestEnvironment();

describe('CollectLargeFileFlowDetails', () => {
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

  it('shows download button', () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowDetails);
    const largeFileArgs: CollectLargeFileFlowArgs = {
      pathSpec: {path: '/path/to/file', pathtype: PathSpecPathType.OS},
      signedUrl: 'http://signed/url',
    };

    const menuItems = fixture.componentInstance.getExportMenuItems(
      newCollectLargeFileFlow({
        name: 'CollectLargeFileFlow',
        args: largeFileArgs,
        state: FlowState.FINISHED,
      }),
      '' /** exportCommandPrefix can be left empty for testing purposes */,
    );
    expect(menuItems.length).toBe(1);
    expect(menuItems[0].title).toMatch('Download Encrypted File');
    expect(menuItems[0].url).toMatch('http://signed/url');
  });

  it('shows flow result in result accordion', async () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowDetails);

    const largeFileArgs: CollectLargeFileFlowArgs = {
      pathSpec: {path: '/path/to/file', pathtype: PathSpecPathType.OS},
      signedUrl: 'http://signed/url',
    };
    fixture.componentInstance.flow = newFlow({
      name: 'CollectLargeFileFlow',
      args: largeFileArgs,
      resultCounts: [{type: 'CollectLargeFileFlowResult', count: 1}],
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness = await harnessLoader.getHarness(
      ResultAccordionHarness,
    );
    await resultAccordionHarness.toggle();
    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledTimes(1);

    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'CollectLargeFileFlowResult',
        payload: {
          sessionUri: 'http://testuri',
          totalBytesSent: '102400',
        },
      }),
    ]);

    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('100.00 KiB');
    expect(fixture.nativeElement.textContent).toContain('http://testuri');
  });
});
