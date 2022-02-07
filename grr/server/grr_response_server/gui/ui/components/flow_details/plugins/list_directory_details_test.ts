import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ListDirectoryDetails} from '../../../components/flow_details/plugins/list_directory_details';
import {newPathSpec} from '../../../lib/api/api_test_util';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {PluginsModule} from './module';




initTestEnvironment();

describe('list-directory-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
          ],

          providers: [],
          teardown: {destroyAfterEach: false}
        })
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
});
