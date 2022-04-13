import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {MultiGetFileDetails} from '../../../components/flow_details/plugins/multi_get_file_details';
import {PathSpecProgressStatus} from '../../../lib/api/api_interfaces';
import {newPathSpec} from '../../../lib/api/api_test_util';
import {newFlow} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {PluginsModule} from './module';



initTestEnvironment();

describe('multi-get-file-details component', () => {
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

  const FLOW_LIST_ENTRY = Object.freeze(newFlow({
    name: 'MultiGetFile',
    args: {
      pathspecs: [
        newPathSpec('/path1'),
        newPathSpec('/path2'),
      ]
    },
    progress: {
      numSkipped: 1,
      numCollected: 1,
      numFailed: 0,

      pathspecsProgress: [
        {
          pathspec: newPathSpec('/path1'),
          status: PathSpecProgressStatus.SKIPPED,
        },
        {
          pathspec: newPathSpec('/path2'),
          status: PathSpecProgressStatus.COLLECTED,
        },
      ]
    },
  }));

  it('shows summary (zero results)', () => {
    const fixture = TestBed.createComponent(MultiGetFileDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'MultiGetFile',
      args: {},
      progress: {
        numSkipped: 0,
        numCollected: 0,
        numFailed: 0,
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('No paths specified');
    expect(fixture.nativeElement.innerText).not.toContain('/path');
  });

  it('shows summary (single path)', () => {
    const fixture = TestBed.createComponent(MultiGetFileDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'MultiGetFile',
      args: {pathspecs: [newPathSpec('/path1')]},
      progress: {
        numFailed: 1,
        pathspecsProgress: [
          {
            pathspec: newPathSpec('/path1'),
            status: PathSpecProgressStatus.FAILED,
          },
        ]
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/path1');
  });

  it('shows summary (multiple paths)', () => {
    const fixture = TestBed.createComponent(MultiGetFileDetails);
    fixture.componentInstance.flow = FLOW_LIST_ENTRY;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/path1 + 1 more');
  });
});
