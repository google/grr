import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {CollectSingleFileDetails} from '@app/components/flow_details/plugins/collect_single_file_details';
import {CollectSingleFileArgs, CollectSingleFileProgress, CollectSingleFileProgressStatus, PathSpecPathType} from '@app/lib/api/api_interfaces';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';




initTestEnvironment();

describe('collect-single-file-details component', () => {
  beforeEach(waitForAsync(() => {
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

    expect(fixture.nativeElement.innerText).toContain('legacy UI');
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

  it('does not show path type note when path type is OS', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.COLLECTED,
      result: {
        stat: {
          pathspec: {
            path: '/foo/bar',
            pathtype: PathSpecPathType.OS,
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

    expect(fixture.nativeElement.innerText)
        .not.toContain('File was fetched by parsing the raw disk image');
  });

  it('shows path type note when path type is NTFS', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.COLLECTED,
      result: {
        stat: {
          pathspec: {
            path: '/foo/bar',
            pathtype: PathSpecPathType.NTFS,
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

    expect(fixture.nativeElement.innerText)
        .toContain(
            'File was fetched by parsing the raw disk image with libfsntfs');
  });

  it('shows path type note when path type is TSK', () => {
    const args: CollectSingleFileArgs = {path: '/foo/bar'};
    const progress: CollectSingleFileProgress = {
      status: CollectSingleFileProgressStatus.COLLECTED,
      result: {
        stat: {
          pathspec: {
            path: '/foo/bar',
            pathtype: PathSpecPathType.TSK,
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

    expect(fixture.nativeElement.innerText)
        .toContain(
            'File was fetched by parsing the raw disk image with libtsk');
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

    expect(fixture.nativeElement.innerText).toContain('File not found');
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
