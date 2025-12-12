import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  FileFinderResult as ApiFileFinderResult,
  StatEntryRegistryType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowResult} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {PathSpecPathType} from '../../../lib/models/vfs';
import {initTestEnvironment} from '../../../testing';
import {FileFinderResults} from './file_finder_results';
import {FileFinderResultsHarness} from './testing/file_finder_results_harness';

initTestEnvironment();

async function createComponent(results: readonly FlowResult[]) {
  const fixture = TestBed.createComponent(FileFinderResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FileFinderResultsHarness,
  );

  return {fixture, harness};
}

describe('File Finder Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FileFinderResults, NoopAnimationsModule],
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

  it('shows a single file finder result with a file', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            stSize: '123',
            pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
          },
          hashEntry: {
            sha256: 'testhash',
          },
        } as ApiFileFinderResult,
      }),
    ]);

    const fileResultsTable = await harness.fileResultsTable();
    expect(await fileResultsTable!.getRows()).toHaveSize(1);
    expect(await fileResultsTable!.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable!.getCellText(0, 'size')).toContain('123');
    expect(await fileResultsTable!.getCellText(0, 'hashes')).toContain(
      'SHA-256',
    );
    expect(await harness.registryResultsTable()).toBeNull();
  }));

  it('shows multiple file finder results with files', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            stSize: '123',
            pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
          },
          hashEntry: {
            sha256: btoa('testhash'),
          },
        } as ApiFileFinderResult,
      }),
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            stSize: '456',
            pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
          },
          hashEntry: {
            md5: btoa('testhash2'),
          },
        } as ApiFileFinderResult,
      }),
    ]);

    const fileResultsTable = await harness.fileResultsTable();
    expect(await fileResultsTable!.getRows()).toHaveSize(2);
    expect(await fileResultsTable!.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable!.getCellText(0, 'size')).toContain('123');
    expect(await fileResultsTable!.getCellText(0, 'hashes')).toContain(
      'SHA-256',
    );
    expect(await fileResultsTable!.getCellText(1, 'path')).toContain('/bar');
    expect(await fileResultsTable!.getCellText(1, 'size')).toContain('456');
    expect(await fileResultsTable!.getCellText(1, 'hashes')).toContain('MD5');
    expect(await harness.registryResultsTable()).toBeNull();
  }));

  it('shows a single file finder result with a registry key', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            registryType: StatEntryRegistryType.REG_SZ,
            pathspec: {
              path: '\\foo\\bar\\{123}\\BAZ',
              pathtype: PathSpecPathType.OS,
            },
            registryData: {
              string: '123',
            },
          },
        } as ApiFileFinderResult,
      }),
    ]);

    const registryResultsTable = await harness.registryResultsTable();
    expect(await registryResultsTable!.getRows()).toHaveSize(1);
    expect(await registryResultsTable!.getCellText(0, 'path')).toContain(
      '\\foo\\bar\\{123}\\BAZ',
    );
    expect(await registryResultsTable!.getCellText(0, 'value')).toContain(
      '123',
    );
    expect(await registryResultsTable!.getCellText(0, 'type')).toContain(
      'REG_SZ',
    );
    expect(await harness.fileResultsTable()).toBeNull();
  }));

  it('shows multiple file finder results with registry keys and values', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            registryType: StatEntryRegistryType.REG_SZ,
            pathspec: {
              path: '\\foo\\bar\\{123}\\BAZ',
              pathtype: PathSpecPathType.OS,
            },
            registryData: {
              string: '123',
            },
          },
        } as ApiFileFinderResult,
      }),
      newFlowResult({
        payloadType: PayloadType.FILE_FINDER_RESULT,
        payload: {
          statEntry: {
            pathspec: {
              path: '\\foo\\bar\\{123}\\BAZ',
              pathtype: PathSpecPathType.REGISTRY,
            },
          },
        } as ApiFileFinderResult,
      }),
    ]);

    const registryResultsTable = await harness.registryResultsTable();
    expect(await registryResultsTable!.getRows()).toHaveSize(2);
    expect(await registryResultsTable!.getCellText(0, 'path')).toContain(
      '\\foo\\bar\\{123}\\BAZ',
    );
    expect(await registryResultsTable!.getCellText(0, 'value')).toContain(
      '123',
    );
    expect(await registryResultsTable!.getCellText(0, 'type')).toContain(
      'REG_SZ',
    );

    expect(await registryResultsTable!.getCellText(1, 'path')).toContain(
      '\\foo\\bar\\{123}\\BAZ',
    );
    expect(await registryResultsTable!.getCellText(1, 'type')).toContain(
      'REG_KEY',
    );
    expect(await harness.fileResultsTable()).toBeNull();
  }));
});
