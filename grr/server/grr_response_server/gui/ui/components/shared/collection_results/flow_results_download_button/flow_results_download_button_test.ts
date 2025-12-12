import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderActionAction} from '../../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../../lib/api/http_api_with_translation_test_util';
import {Flow, FlowState, FlowType} from '../../../../lib/models/flow';
import {newFlow} from '../../../../lib/models/model_test_util';
import {GlobalStore} from '../../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../../store/store_test_util';
import {initTestEnvironment} from '../../../../testing';
import {FlowResultsDownloadButton} from './flow_results_download_button';
import {FlowResultsDownloadButtonHarness} from './testing/flow_results_download_button_harness';

initTestEnvironment();

async function createComponent(flow?: Flow) {
  const fixture = TestBed.createComponent(FlowResultsDownloadButton);
  fixture.componentRef.setInput('flow', flow);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowResultsDownloadButtonHarness,
  );
  return {fixture, harness};
}

describe('Flow Results Download Button Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowResultsDownloadButton, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture, harness} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
    expect(harness).toBeTruthy();
  });

  it('does not show download options when flow is not finished', async () => {
    const flow = newFlow({
      name: 'ArtifactCollectorFlow',
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      resultCounts: [{type: 'StatEntry', count: 1}],
      state: FlowState.RUNNING,
    });
    const {harness} = await createComponent(flow);

    expect(await harness.hasDownloadButton()).toBeFalse();
  });

  it('does not show download options when flow has no results', async () => {
    const flow = newFlow({
      name: 'ArtifactCollectorFlow',
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      resultCounts: [{type: 'StatEntry', count: 0}],
      state: FlowState.FINISHED,
    });
    const {harness} = await createComponent(flow);

    expect(await harness.hasDownloadButton()).toBeFalse();
  });

  it('does not show download options when flow has no flow type', async () => {
    const flow = newFlow({
      name: 'ArtifactCollectorFlow',
      resultCounts: [{type: 'StatEntry', count: 1}],
      state: FlowState.FINISHED,
      flowType: undefined,
    });
    const {harness} = await createComponent(flow);

    expect(await harness.hasDownloadButton()).toBeFalse();
  });

  it('shows download options when flow is finished and has results', async () => {
    const flow = newFlow({
      name: 'ArtifactCollectorFlow',
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      resultCounts: [{type: 'StatEntry', count: 1}],
      state: FlowState.FINISHED,
    });
    const {harness} = await createComponent(flow);

    expect(await harness.hasDownloadButton()).toBeTrue();
    const downloadMenu = await harness.openDownloadMenu();
    const menuItems = await downloadMenu.getItems();
    expect(menuItems).toHaveSize(4);
    expect(await menuItems[0].getText()).toBe('Download files');
    expect(await menuItems[1].getText()).toBe('Download CSV');
    expect(await menuItems[2].getText()).toBe('Download YAML');
    expect(await menuItems[3].getText()).toBe('Download SQLite');
  });

  it('has `Copy cli command` option when export command prefix is set', async () => {
    globalStoreMock.exportCommandPrefix = signal('export_command_prefix');
    const flow = newFlow({
      name: 'ArtifactCollectorFlow',
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      resultCounts: [{type: 'StatEntry', count: 1}],
      state: FlowState.FINISHED,
    });
    const {harness} = await createComponent(flow);

    const downloadMenu = await harness.openDownloadMenu();
    const menuItems = await downloadMenu.getItems();
    expect(menuItems).toHaveSize(5);
    expect(await menuItems[4].getText()).toBe('Copy CLI Command');
  });

  describe('for OS_QUERY_FLOW', () => {
    it('has `Download files` option when flow has fileCollectionColumns progress contains totalRowCount', async () => {
      const flow = newFlow({
        name: 'OsqueryFlow',
        flowType: FlowType.OS_QUERY_FLOW,
        resultCounts: [{type: 'OsqueryResult', count: 1}],
        progress: {
          totalRowCount: 1,
        },
        args: {
          fileCollectionColumns: ['file_collection_column'],
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeTrue();
    });

    it('does not have `Download files` option when flow has no fileCollectionColumns', async () => {
      const flow = newFlow({
        name: 'OsqueryFlow',
        flowType: FlowType.OS_QUERY_FLOW,
        resultCounts: [{type: 'OsqueryResult', count: 1}],
        progress: {
          totalRowCount: 1,
        },
        args: {
          fileCollectionColumns: [],
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeFalse();
    });

    it('does not show `Download files` option when flow has no totalRowCount', async () => {
      const flow = newFlow({
        name: 'OsqueryFlow',
        flowType: FlowType.OS_QUERY_FLOW,
        resultCounts: [{type: 'OsqueryResult', count: 1}],
        progress: {
          totalRowCount: 0,
        },
        args: {
          fileCollectionColumns: ['file_collection_column'],
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeFalse();
    });
  });

  describe('for COLLECT_BROWSER_HISTORY', () => {
    it('has `Download files` option when flow has CollectBrowserHistoryResult results', async () => {
      const flow = newFlow({
        name: 'CollectBrowserHistory',
        flowType: FlowType.COLLECT_BROWSER_HISTORY,
        resultCounts: [{type: 'CollectBrowserHistoryResult', count: 1}],
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeTrue();
    });

    it('does not have `Download files` option when flow has no CollectBrowserHistoryResult results', async () => {
      const flow = newFlow({
        name: 'CollectBrowserHistory',
        flowType: FlowType.COLLECT_BROWSER_HISTORY,
        resultCounts: [{type: 'StatEntry', count: 1}],
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeFalse();
    });
  });

  describe('for FILE_FINDER', () => {
    it('has `Download files` when flow has action type DOWNLOAD', async () => {
      const flow = newFlow({
        name: 'FileFinder',
        flowType: FlowType.FILE_FINDER,
        resultCounts: [{type: 'FileFinderResult', count: 1}],
        args: {
          action: {
            actionType: FileFinderActionAction.DOWNLOAD,
          },
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeTrue();
    });

    it('does not have `Download files` option when flow has no action type DOWNLOAD', async () => {
      const flow = newFlow({
        name: 'FileFinder',
        flowType: FlowType.FILE_FINDER,
        resultCounts: [{type: 'FileFinderResult', count: 1}],
        args: {
          action: {
            actionType: FileFinderActionAction.STAT,
          },
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download files')).toBeFalse();
    });
  });

  describe('for READ_LOW_LEVEL', () => {
    it('has custom `Download data` button', async () => {
      const flow = newFlow({
        name: 'ReadLowLevel',
        flowType: FlowType.READ_LOW_LEVEL,
        resultCounts: [{type: 'ReadLowLevelResult', count: 1}],
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(await harness.hasDownloadMenuItem('Download data')).toBeTrue();
    });
  });

  describe('for TIMELINE_FLOW', () => {
    it('has custom `Download body file` buttons', async () => {
      const flow = newFlow({
        name: 'TimelineFlow',
        flowType: FlowType.TIMELINE_FLOW,
        resultCounts: [{type: 'TimelineResult', count: 1}],
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(
        await harness.hasDownloadMenuItem('Download body file'),
      ).toBeTrue();
      expect(
        await harness.hasDownloadMenuItem(
          'Download body file (Windows format)',
        ),
      ).toBeTrue();
    });
  });
  describe('for COLLECT_LARGE_FILE_FLOW', () => {
    it('has custom `Download encrypted file` button', async () => {
      const flow = newFlow({
        name: 'CollectLargeFileFlow',
        flowType: FlowType.COLLECT_LARGE_FILE_FLOW,
        resultCounts: [{type: 'CollectLargeFileResult', count: 1}],
        args: {
          signedUrl: 'https://www.google.com',
        },
        state: FlowState.FINISHED,
      });
      const {harness} = await createComponent(flow);

      expect(
        await harness.hasDownloadMenuItem('Download encrypted file'),
      ).toBeTrue();
    });
  });
});
