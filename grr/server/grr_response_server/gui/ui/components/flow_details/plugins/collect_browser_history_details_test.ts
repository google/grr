import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {CollectBrowserHistoryDetails} from '@app/components/flow_details/plugins/collect_browser_history_details';
import {BrowserProgressStatus, CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser, CollectBrowserHistoryProgress, CollectBrowserHistoryResult} from '@app/lib/api/api_interfaces';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResult} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';

import {PluginsModule} from './module';




initTestEnvironment();

describe('collect-browser-history-details component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
          ],

          providers: []
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
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

    fixture.componentInstance.flow = newFlow({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.in-progress')).nativeElement)
        .toBeDefined();
  });

  it('emits results query on browser title link', () => {
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

    fixture.componentInstance.flow = newFlow({
      clientId: 'C.1',
      flowId: '12',
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    expect(flowResultsLocalStore.queryMore).not.toHaveBeenCalled();

    const title = fixture.debugElement.query(By.css('.title')).nativeElement;
    title.click();

    expect(flowResultsLocalStore.queryMore)
        .toHaveBeenCalledWith(fixture.componentInstance.INITIAL_COUNT);
  });

  it('loads and displays file results', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: CollectBrowserHistoryArgsBrowser.CHROME,
        status: BrowserProgressStatus.SUCCESS,
        numCollectedFiles: 200,
      }],
    };

    fixture.componentInstance.flow = newFlow({
      clientId: 'C.1',
      flowId: '12',
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const title = fixture.debugElement.query(By.css('.title')).nativeElement;
    title.click();

    expect(flowResultsLocalStore.queryMore)
        .toHaveBeenCalledOnceWith(fixture.componentInstance.INITIAL_COUNT);

    flowResultsLocalStore.resultsSubject.next(
        [...new Array(100)].map((v, i) => newFlowResult({
                                  payload: makeBrowserHistoryResult(i),
                                  tag: 'CHROME',
                                  payloadType: 'CollectBrowserHistoryResult',
                                })));
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/browser/99.txt');


    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledTimes(1);

    fixture.debugElement.query(By.css('button.load-more'))
        .nativeElement.click();
    fixture.detectChanges();

    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledTimes(2);
    expect(flowResultsLocalStore.queryMore)
        .toHaveBeenCalledWith(fixture.componentInstance.LOAD_STEP);

    flowResultsLocalStore.resultsSubject.next(
        [...new Array(200)].map((v, i) => newFlowResult({
                                  payload: makeBrowserHistoryResult(i),
                                  tag: 'CHROME',
                                  payloadType: 'CollectBrowserHistoryResult',
                                })));
  });
});

function makeBrowserHistoryResult(i: number): CollectBrowserHistoryResult {
  return {
    browser: CollectBrowserHistoryArgsBrowser.CHROME,
    statEntry: {pathspec: {path: `/browser/${i}.txt`}}
  };
}
