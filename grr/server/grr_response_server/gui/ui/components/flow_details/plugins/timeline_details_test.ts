import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';

import {encodeStringToBase64} from '../../../lib/api_translation/primitive';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

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
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('should display a download button when the flow is finished', () => {
    const fixture = TestBed.createComponent(TimelineDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'TimelineFlow',
      clientId: 'C.1234',
      flowId: 'ABCDEF',
      state: FlowState.FINISHED,
      args: {
        root: encodeStringToBase64('/'),
      },
    });
    fixture.detectChanges();

    const button = fixture.debugElement.query(
        By.css('.download.flow-details-summary-actions > a'));
    expect(button.nativeElement.innerText).toBe('Download body');

    const url = new URL(button.properties['href']);
    expect(url.pathname).toContain('C.1234');
    expect(url.pathname).toContain('ABCDEF');

    expect(button.properties['download']).toContain('.body');
    expect(button.properties['download']).toContain('1234');
    expect(button.properties['download']).toContain('ABCDEF');
  });

  it('should allow customizing output format of the body export', () => {
    const fixture = TestBed.createComponent(TimelineDetails);

    fixture.componentInstance.flow = newFlow({
      name: 'TimelineFlow',
      clientId: 'C.1234',
      flowId: 'ABCDEF',
      state: FlowState.FINISHED,
      args: {
        root: encodeStringToBase64('/'),
      },
    });
    fixture.detectChanges();

    fixture.componentInstance.bodyOptsForm.setValue({
      timestampSubsecondPrecision: false,
      inodeNtfsFileReferenceFormat: true,
      backslashEscape: true,
      carriageReturnEscape: true,
      nonPrintableEscape: true,
    });
    fixture.detectChanges();

    const button = fixture.debugElement.query(
        By.css('.download.flow-details-summary-actions > a'));

    const params = new URL(button.properties['href']).searchParams;
    expect(params.get('body_opts.timestamp_subsecond_precision')).toBe('0');
    expect(params.get('body_opts.inode_ntfs_file_reference_format')).toBe('1');
    expect(params.get('body_opts.backslash_escape')).toBe('1');
    expect(params.get('body_opts.carriage_return_escape')).toBe('1');
    expect(params.get('body_opts.non_printable_escape')).toBe('1');
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

    expect(fixture.nativeElement.innerText).toContain('/foo/bar/baz');
  });
});
