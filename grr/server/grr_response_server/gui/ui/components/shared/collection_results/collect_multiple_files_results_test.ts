import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectMultipleFilesResult as ApiCollectMultipleFilesResult,
  CollectMultipleFilesResultStatus,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowResult} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectMultipleFilesResults} from './collect_multiple_files_results';
import {CollectMultipleFilesResultsHarness} from './testing/collect_multiple_files_results_harness';

initTestEnvironment();

async function createComponent(results: readonly FlowResult[]) {
  const fixture = TestBed.createComponent(CollectMultipleFilesResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectMultipleFilesResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Multiple Files Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectMultipleFilesResults, NoopAnimationsModule],
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

  it('shows no table if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.fileResultsTables()).toBeNull();
  }));

  it('shows a single file result', fakeAsync(async () => {
    const collectMultipleFilesResult: ApiCollectMultipleFilesResult = {
      stat: {
        pathspec: {path: '/foo', pathtype: PathSpecPathType.TSK},
        stSize: '123',
      },
      hash: {md5: 'md5hash', sha1: 'sha1hash', sha256: 'sha256hash'},
      status: CollectMultipleFilesResultStatus.COLLECTED,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: collectMultipleFilesResult,
      }),
    ]);

    const fileResultsTable = await harness.fileResultsTables();
    expect(fileResultsTable).toBeDefined();
    expect(await fileResultsTable!.getRows()).toHaveSize(1);
    expect(await fileResultsTable!.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable!.getCellText(0, 'size')).toContain('123');
    expect(await fileResultsTable!.getCellText(0, 'hashes')).toContain(
      'SHA-256 + 2',
    );
  }));

  it('shows multiple results', fakeAsync(async () => {
    const collectMultipleFilesResult: ApiCollectMultipleFilesResult = {
      stat: {
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        stSize: '123',
      },
      hash: {md5: 'md5hash', sha1: 'sha1hash', sha256: 'sha256hash'},
      status: CollectMultipleFilesResultStatus.COLLECTED,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: collectMultipleFilesResult,
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: collectMultipleFilesResult,
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: collectMultipleFilesResult,
      }),
    ]);

    const fileResultsTable = await harness.fileResultsTables();
    expect(fileResultsTable).toBeDefined();

    expect(await fileResultsTable!.getRows()).toHaveSize(3);
  }));
});
