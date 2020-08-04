import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {CollectSingleFileDetails} from '@app/components/flow_details/plugins/collect_single_file_details';
import {CollectSingleFileArgs, CollectSingleFileProgress, CollectSingleFileProgressStatus} from '@app/lib/api/api_interfaces';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';




initTestEnvironment();

describe('collect-single-file-details component', () => {
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
          ],

          providers: []
        })
        .compileComponents();
  }));

  it('shows message if progress is not reported', () => {
    const fixture = TestBed.createComponent(CollectSingleFileDetails);

    fixture.componentInstance.flowListEntry =
        newFlowListEntry({name: 'CollectSingleFile'});
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('The flow didn\'t report its progress');
  });

  it('does not show download button when result is reported', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.IN_PROGRESS,
    };

    const fixture = TestBed.createComponent(CollectSingleFileDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectSingleFile',
      args,
      progress,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Download');
  });

  it('shows download button when result is reported', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.COLLECTED,
      result: {
        stat: {
          pathspec: {
            path: '/foo/bar',
          }
        }
      },
    };

    const fixture = TestBed.createComponent(CollectSingleFileDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectSingleFile',
      args,
      progress,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Download');
  });

  it('shows an error message when file is not found', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.NOT_FOUND,
    };

    const fixture = TestBed.createComponent(CollectSingleFileDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectSingleFile',
      args,
      progress,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Not found');
  });

  it('shows and error message on failure', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.FAILED,
      errorDescription: 'Some error'
    };

    const fixture = TestBed.createComponent(CollectSingleFileDetails);
    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectSingleFile',
      args,
      progress,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Some error');
  });
});
