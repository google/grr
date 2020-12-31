import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {CollectMultipleFilesArgs, CollectMultipleFilesProgress} from '@app/lib/api/api_interfaces';
import {FlowState} from '@app/lib/models/flow';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {CollectMultipleFilesDetails} from './collect_multiple_files_details';
import {PluginsModule} from './module';



initTestEnvironment();

describe('collect-multiple-files-details component', () => {
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


  it('does not show "Download all" button on non-finished flow', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesDetails);
    const args: CollectMultipleFilesArgs = {pathExpressions: ['/foo/**']};
    const progress: CollectMultipleFilesProgress = {
      numCollected: '0',
      numFound: '1',
      numInProgress: '1',
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectMultipleFiles',
      args,
      progress,
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Download all');
  });

  it('does not show "Download all" button on 0 files found', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesDetails);
    const args: CollectMultipleFilesArgs = {pathExpressions: ['/foo/**']};
    const progress: CollectMultipleFilesProgress = {
      numCollected: '0',
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectMultipleFiles',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('0 files');
    expect(fixture.nativeElement.innerText).not.toContain('Download all');
  });

  it('shows "Download all" button on finished flow with >1 results', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesDetails);
    const args: CollectMultipleFilesArgs = {pathExpressions: ['/foo/**']};
    const progress: CollectMultipleFilesProgress = {
      numCollected: '42',
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectMultipleFiles',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('42 files');

    // Check that the download button has a correct href attribute.
    const downloadButton: HTMLLinkElement =
        fixture.nativeElement.querySelector('.download a');
    expect(downloadButton.innerText).toContain('Download all');
    expect(downloadButton.getAttribute('href'))
        .toMatch('/api/v2/clients/.+/flows/.+/results/files-archive');
  });
});
