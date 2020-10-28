import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {CollectBrowserHistoryDetails} from '@app/components/flow_details/plugins/collect_browser_history_details';
import {FlowResultsQueryWithoutFlowId} from '@app/components/flow_details/plugins/plugin';
import {BrowserProgressStatus, CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser, CollectBrowserHistoryProgress} from '@app/lib/api/api_interfaces';
import {FlowState} from '@app/lib/models/flow';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';




initTestEnvironment();

describe('collect-browser-history-details component', () => {
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
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);

    fixture.componentInstance.flowListEntry =
        newFlowListEntry({name: 'CollectBrowserHistory'});
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('legacy UI');
  });

  it('does not show "Download all" button on non-finished flow', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 20,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Total');
    expect(fixture.nativeElement.innerText).not.toContain('Download all');
  });

  it('does not show "Download all" button on 0 files found', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 0,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Total');
    expect(fixture.nativeElement.innerText).not.toContain('Download all');
  });

  it('shows "Download all" button on finished flow with >1 results', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [
        CollectBrowserHistoryArgsBrowser.CHROME,
        CollectBrowserHistoryArgsBrowser.OPERA,
        CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER
      ],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [
        {
          browser: CollectBrowserHistoryArgsBrowser.CHROME,
          status: BrowserProgressStatus.SUCCESS,
          numCollectedFiles: 20,
        },
        {
          browser: CollectBrowserHistoryArgsBrowser.OPERA,
          status: BrowserProgressStatus.SUCCESS,
          numCollectedFiles: 22,
        },
        {
          browser: CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER,
          status: BrowserProgressStatus.ERROR,
          description: 'Something happened.',
        },
      ],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
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

  it('shows per-browser details', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.IN_PROGRESS,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('Chrome');
  });

  it('shows warning on per-browser success with 0 results', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 0,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(
        fixture.debugElement.query(By.css('.warning')).nativeElement.innerText)
        .toContain('No files collected');
  });

  it('shows error on per-browser error', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.ERROR,
        description: 'Something happened',
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.error')).nativeElement.innerText)
        .toContain('Something happened');
  });

  it('shows number of files on per-browser success', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 42,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(
        fixture.debugElement.query(By.css('.success')).nativeElement.innerText)
        .toContain('42 files');
  });

  it('shows a spinner on per-browser in-progress state', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.IN_PROGRESS,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.in-progress')).nativeElement)
        .toBeDefined();
  });

  it('emits results query on browser title link', (done) => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 42,
      }],
    };

    fixture.componentInstance.flowListEntry = newFlowListEntry({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    fixture.componentInstance.flowResultsQuery.subscribe(
        (e: FlowResultsQueryWithoutFlowId) => {
          expect(e).toEqual({
            offset: 0,
            count: CollectBrowserHistoryDetails.INITIAL_COUNT,
            withTag: 'CHROME',
          });
          done();
        });

    const title = fixture.debugElement.query(By.css('.title')).nativeElement;
    title.click();
  });
});
