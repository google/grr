import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  Browser as ApiBrowser,
  CollectBrowserHistoryResult as ApiCollectBrowserHistoryResult,
  StatEntry as ApiStatEntry,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowResult} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectBrowserHistoryResults} from './collect_browser_history_results';
import {CollectBrowserHistoryResultsHarness} from './testing/collect_browser_history_results_harness';

initTestEnvironment();

async function createComponent(results: readonly FlowResult[]) {
  const fixture = TestBed.createComponent(CollectBrowserHistoryResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectBrowserHistoryResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Browser History Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectBrowserHistoryResults, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows a browser history result', fakeAsync(async () => {
    const browserHistoryResult: ApiCollectBrowserHistoryResult = {
      browser: ApiBrowser.CHROMIUM_BASED_BROWSERS,
      statEntry: {
        stSize: '123',
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      } as ApiStatEntry,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
        payload: browserHistoryResult,
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(1);
    const chromiumTable = await harness.getTableForBrowser(
      ApiBrowser.CHROMIUM_BASED_BROWSERS,
    );
    expect(await chromiumTable.getRows()).toHaveSize(1);
    expect(await chromiumTable.getCellText(0, 'path')).toContain('/foo');
    expect(await chromiumTable.getCellText(0, 'size')).toContain('123');
  }));

  it('shows several browser history results from a single browser', fakeAsync(async () => {
    const browserHistoryResult1: ApiCollectBrowserHistoryResult = {
      browser: ApiBrowser.FIREFOX,
      statEntry: {
        stSize: '123',
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      } as ApiStatEntry,
    };
    const browserHistoryResult2: ApiCollectBrowserHistoryResult = {
      browser: ApiBrowser.FIREFOX,
      statEntry: {
        stSize: '234',
        pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
      } as ApiStatEntry,
    };

    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
        payload: browserHistoryResult1,
      }),
      newFlowResult({
        payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
        payload: browserHistoryResult2,
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(1);
    const chromiumTable = await harness.getTableForBrowser(ApiBrowser.FIREFOX);
    expect(await chromiumTable.getRows()).toHaveSize(2);
    expect(await chromiumTable.getCellText(0, 'path')).toContain('/foo');
    expect(await chromiumTable.getCellText(0, 'size')).toContain('123');
    expect(await chromiumTable.getCellText(1, 'path')).toContain('/bar');
    expect(await chromiumTable.getCellText(1, 'size')).toContain('234');
  }));

  it('shows results from different browsers in different tables', fakeAsync(async () => {
    const browserHistoryChromium: ApiCollectBrowserHistoryResult = {
      browser: ApiBrowser.CHROMIUM_BASED_BROWSERS,
      statEntry: {
        stSize: '123',
        pathspec: {path: '/foo', pathtype: PathSpecPathType.TSK},
      } as ApiStatEntry,
    };
    const browserHistoryFirefox: ApiCollectBrowserHistoryResult = {
      browser: ApiBrowser.FIREFOX,
      statEntry: {
        stSize: '234',
        pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
      } as ApiStatEntry,
    };

    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
        payload: browserHistoryChromium,
      }),
      newFlowResult({
        payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
        payload: browserHistoryFirefox,
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(2);
    const chromiumTable = await harness.getTableForBrowser(
      ApiBrowser.CHROMIUM_BASED_BROWSERS,
    );
    expect(await chromiumTable.getRows()).toHaveSize(1);
    expect(await chromiumTable.getCellText(0, 'path')).toContain('/foo');
    expect(await chromiumTable.getCellText(0, 'size')).toContain('123 B');
    const firefoxTable = await harness.getTableForBrowser(ApiBrowser.FIREFOX);
    expect(await firefoxTable.getRows()).toHaveSize(1);
    expect(await firefoxTable.getCellText(0, 'path')).toContain('/bar');
    expect(await firefoxTable.getCellText(0, 'size')).toContain('234 B');
  }));
});
