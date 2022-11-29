import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ListDirectoryDetails} from '../../../components/flow_details/plugins/list_directory_details';
import {PathSpecPathType, StatEntry} from '../../../lib/api/api_interfaces';
import {newPathSpec} from '../../../lib/api/api_test_util';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {PluginsModule} from './module';



initTestEnvironment();

describe('list-directory-details component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RouterTestingModule,
            PluginsModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('does NOT show summary (zero results)', () => {
    const fixture = TestBed.createComponent(ListDirectoryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'ListDirectory',
      args: {},
      resultCounts: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('No paths specified');
    expect(fixture.nativeElement.innerText).not.toContain('/paths');
  });

  it('shows summary', () => {
    const fixture = TestBed.createComponent(ListDirectoryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'ListDirectory',
      clientId: 'C.1234',
      flowId: '5678',
      args: {
        pathspec: newPathSpec('/paths'),
      },
      state: FlowState.FINISHED,
      resultCounts: [{type: 'StatEntry', count: 42}],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/paths');
  });

  it('shows summary for RecursiveListDirectory', () => {
    const fixture = TestBed.createComponent(ListDirectoryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'RecursiveListDirectory',
      clientId: 'C.1234',
      flowId: '5678',
      args: {
        pathspec: newPathSpec('/paths'),
      },
      state: FlowState.FINISHED,
      resultCounts: [{type: 'StatEntry', count: 42}],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/paths');
  });

  it('shows results', async () => {
    const fixture = TestBed.createComponent(ListDirectoryDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'ListDirectory',
      clientId: 'C.1234',
      flowId: '5678',
      args: {
        pathspec: newPathSpec('/foo'),
      },
      state: FlowState.FINISHED,
      resultCounts: [{type: 'StatEntry', count: 1}],
    });
    const statEntry: StatEntry = {
      stSize: '123',
      stMtime: '1629144908',
      pathspec: {
        path: '/foo',
        pathtype: PathSpecPathType.OS,
        nestedPath: {path: '/bar', pathtype: PathSpecPathType.TSK}
      },
    };
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();
    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payloadType: 'StatEntry', payload: statEntry})]);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('/foo/bar');
    expect(fixture.nativeElement.innerText).toContain('2021-08-16');
  });
});
