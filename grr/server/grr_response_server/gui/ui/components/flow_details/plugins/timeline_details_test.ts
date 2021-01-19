import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';
import {FlowState} from '../../../lib/models/flow';

import {PluginsModule} from './module';

import {TimelineDetails} from './timeline_details';


initTestEnvironment();

describe('timeline-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],

        })
        .compileComponents();
  }));

  it('should display a download button when the flow is finished', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'TimelineFlow',
      clientId: 'C.1234',
      flowId: 'ABCDEF',
      state: FlowState.FINISHED,
      args: {
        root: '/',
      },
    });
    fixture.detectChanges();

    const button = fixture.debugElement.query(
        By.css('.download.flow-details-summary-actions > a'));
    expect(button.nativeElement.innerText).toBe('Download body');
    expect(button.properties['href']).toContain('1234');
    expect(button.properties['href']).toContain('ABCDEF');
    expect(button.properties['download']).toContain('.body');
    expect(button.properties['download']).toContain('1234');
    expect(button.properties['download']).toContain('ABCDEF');
  });

  it('should display the root path when the flow is still running', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'TimelineFlow',
      state: FlowState.RUNNING,
      args: {
        root: '/foo/bar/baz',
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo/bar/baz');
  });

  it('should display an error message if the flow failed', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'TimelineFlow',
      state: FlowState.ERROR,
      args: {
        root: '/',
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Failed to collect');
  });
});