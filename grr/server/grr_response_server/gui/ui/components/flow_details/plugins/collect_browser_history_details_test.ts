import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {CollectBrowserHistoryDetails} from '../../../components/flow_details/plugins/collect_browser_history_details';
import {Browser, BrowserProgressStatus, CollectBrowserHistoryArgs, CollectBrowserHistoryProgress, CollectBrowserHistoryResult, PathSpecPathType} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

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
            RouterTestingModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('shows per-browser details', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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

  it('shows error after flow has been cancelled', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
        status: BrowserProgressStatus.IN_PROGRESS,
      }],
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectBrowserHistory',
      args,
      progress,
      state: FlowState.ERROR,
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.in-progress'))).toBeNull();
    expect(fixture.debugElement.query(By.css('.error')).nativeElement)
        .toBeTruthy();
  });

  it('emits results query on browser title link', () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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
      browsers: [Browser.CHROME],
    };
    const progress: CollectBrowserHistoryProgress = {
      browsers: [{
        browser: Browser.CHROME,
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

    flowResultsLocalStore.mockedObservables.results$.next(
        Array.from({length: 55}, (v, i) => newFlowResult({
                                   payload: makeBrowserHistoryResult(i),
                                   tag: 'CHROME',
                                   payloadType: 'CollectBrowserHistoryResult',
                                 })));
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/browser/4.txt');

    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledTimes(1);

    fixture.debugElement.query(By.css('button.load-more'))
        .nativeElement.click();
    fixture.detectChanges();

    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledTimes(2);
    expect(flowResultsLocalStore.queryMore)
        .toHaveBeenCalledWith(fixture.componentInstance.LOAD_STEP);

    flowResultsLocalStore.mockedObservables.results$.next(
        [...new Array(200)].map((v, i) => newFlowResult({
                                  payload: makeBrowserHistoryResult(i),
                                  tag: 'CHROME',
                                  payloadType: 'CollectBrowserHistoryResult',
                                })));
  });


  it('displays download options in menu when flow has results', async () => {
    const fixture = TestBed.createComponent(CollectBrowserHistoryDetails);
    const args: CollectBrowserHistoryArgs = {
      browsers: [Browser.CHROME],
    };
    fixture.componentInstance.flow = newFlow({
      clientId: 'C.1',
      flowId: '12',
      name: 'CollectBrowserHistory',
      args,
      resultCounts: [{type: 'CollectBrowserHistoryResult', count: 1}],
      state: FlowState.FINISHED,
    });

    const menuItems = fixture.componentInstance.getExportMenuItems(
        fixture.componentInstance.flow);
    expect(menuItems[0])
        .toEqual(fixture.componentInstance.getDownloadFilesExportMenuItem(
            fixture.componentInstance.flow));
  });
});

function makeBrowserHistoryResult(i: number): CollectBrowserHistoryResult {
  return {
    browser: Browser.CHROME,
    statEntry:
        {pathspec: {path: `/browser/${i}.txt`, pathtype: PathSpecPathType.OS}}
  };
}
