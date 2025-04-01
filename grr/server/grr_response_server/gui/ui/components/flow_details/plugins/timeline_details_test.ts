import {TestBed, waitForAsync} from '@angular/core/testing';

import {encodeStringToBase64} from '../../../lib/api_translation/primitive';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {PluginsModule} from './module';
import {TimelineDetails} from './timeline_details';

initTestEnvironment();

describe('timeline-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [PluginsModule],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('should display collected root path when flow is finished', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'TimelineFlow',
      clientId: 'C.1234',
      flowId: 'ABCDEF',
      state: FlowState.FINISHED,
      args: {
        root: encodeStringToBase64('/foo/bar/baz'),
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toBe('/foo/bar/baz');
  });

  it('should display the root path when the flow is still running', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'TimelineFlow',
      state: FlowState.RUNNING,
      args: {
        root: encodeStringToBase64('/foo/bar/baz'),
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toBe('/foo/bar/baz');
  });
});
