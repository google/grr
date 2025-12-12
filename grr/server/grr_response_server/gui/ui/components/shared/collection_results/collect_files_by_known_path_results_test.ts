import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectFilesByKnownPathResult as ApiCollectFilesByKnownPathResult,
  CollectFilesByKnownPathResultStatus,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowResult} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectFilesByKnownPathResults} from './collect_files_by_known_path_results';
import {CollectFilesByKnownPathResultsHarness} from './testing/collect_files_by_known_path_results_harness';

initTestEnvironment();

async function createComponent(results: readonly FlowResult[]) {
  const fixture = TestBed.createComponent(CollectFilesByKnownPathResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectFilesByKnownPathResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Files By Known Path Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectFilesByKnownPathResults, NoopAnimationsModule],
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

  it('shows a single collected file', fakeAsync(async () => {
    const collectFilesByKnownPathResult: ApiCollectFilesByKnownPathResult = {
      stat: {
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      },
      hash: {
        sha256: 'testhash',
      },
      status: CollectFilesByKnownPathResultStatus.COLLECTED,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: collectFilesByKnownPathResult,
      }),
    ]);

    const table = await harness.fileResultsTables();
    expect(await table.getRows()).toHaveSize(1);
    expect(await table.getCellText(0, 'path')).toContain('/foo');
    expect(await table.getCellText(0, 'hashes')).toContain('SHA-256');
    expect(await table.getStatusIconName(0)).toEqual('check');
  }));

  it('shows a single error', fakeAsync(async () => {
    const collectFilesByKnownPathResult: ApiCollectFilesByKnownPathResult = {
      stat: {
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      },
      error: '#failed',
      status: CollectFilesByKnownPathResultStatus.FAILED,
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: collectFilesByKnownPathResult,
      }),
    ]);

    const table = await harness.fileResultsTables();
    expect(await table.getRows()).toHaveSize(1);
    expect(await table.getCellText(0, 'path')).toContain('/foo');
    expect(await table.getStatusIconName(0)).toEqual('error');
  }));

  it('shows both collected and error results', fakeAsync(async () => {
    const collectFilesByKnownPathResult: ApiCollectFilesByKnownPathResult = {
      stat: {
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      },
      hash: {
        sha256: 'testhash',
      },
      status: CollectFilesByKnownPathResultStatus.COLLECTED,
    };
    const collectFilesByKnownPathError: ApiCollectFilesByKnownPathResult = {
      stat: {
        pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
      },
      error: '#failed',
      status: CollectFilesByKnownPathResultStatus.FAILED,
    };

    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: collectFilesByKnownPathResult,
      }),
      newFlowResult({
        payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
        payload: collectFilesByKnownPathError,
      }),
    ]);

    const fileResultsTable = await harness.fileResultsTables();
    expect(await fileResultsTable.getRows()).toHaveSize(2);
    expect(await fileResultsTable.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable.getCellText(0, 'hashes')).toContain(
      'SHA-256',
    );
    expect(await fileResultsTable.getStatusIconName(0)).toEqual('check');

    expect(await fileResultsTable.getCellText(1, 'path')).toContain('/bar');
    expect(await fileResultsTable.getStatusIconName(1)).toEqual('error');
  }));
});
