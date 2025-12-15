import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  StatEntry as ApiStatEntry,
  StatEntryRegistryType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {PathSpecPathType} from '../../../lib/models/vfs';
import {initTestEnvironment} from '../../../testing';
import {StatEntryResults} from './stat_entry_results';
import {StatEntryResultsHarness} from './testing/stat_entry_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(StatEntryResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    StatEntryResultsHarness,
  );

  return {fixture, harness};
}

describe('Stat Entry Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [StatEntryResults, NoopAnimationsModule],
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

  it('shows a single file result', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(1);
    expect(await harness.registryResultsTables()).toHaveSize(0);
    const fileResultsTable = (await harness.fileResultsTables())[0];
    expect(await fileResultsTable.getRows()).toHaveSize(1);
    expect(await fileResultsTable.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable.getCellText(0, 'size')).toContain('123');
  }));

  it('shows a single registry result', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          registryType: StatEntryRegistryType.REG_BINARY,
          pathspec: {path: 'HKLM\\foo', pathtype: PathSpecPathType.REGISTRY},
        } as ApiStatEntry,
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(0);
    expect(await harness.registryResultsTables()).toHaveSize(1);
    const registryResultsTable = (await harness.registryResultsTables())[0];
    expect(await registryResultsTable.getRows()).toHaveSize(1);
    expect(await registryResultsTable.getCellText(0, 'path')).toContain(
      'HKLM\\foo',
    );
    expect(await registryResultsTable.getCellText(0, 'type')).toContain(
      'REG_BINARY',
    );
  });

  it('shows results with different tags in different tables', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag1',
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '456',
          pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag2',
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          registryType: StatEntryRegistryType.REG_BINARY,
          pathspec: {path: 'HKLM\\foo', pathtype: PathSpecPathType.REGISTRY},
        } as ApiStatEntry,
        tag: 'tag3',
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(2);
    expect(await harness.registryResultsTables()).toHaveSize(1);
  }));

  it('shows results with the same tag in the same table', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag',
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '456',
          pathspec: {path: '/bar', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag',
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(1);
    expect(await harness.registryResultsTables()).toHaveSize(0);
    const fileResultsTable = (await harness.fileResultsTables())[0];
    expect(await fileResultsTable.getRows()).toHaveSize(2);
    expect(await fileResultsTable.getCellText(0, 'path')).toContain('/foo');
    expect(await fileResultsTable.getCellText(0, 'size')).toContain('123');
    expect(await fileResultsTable.getCellText(1, 'path')).toContain('/bar');
    expect(await fileResultsTable.getCellText(1, 'size')).toContain('456');
  }));

  it('shows results with no tag in no collapsible container', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
      }),
    ]);

    expect(await harness.collapsibleContainers()).toHaveSize(0);
  }));

  it('shows results with tags in separate collapsible containers', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag1',
      }),
      newFlowResult({
        payloadType: PayloadType.STAT_ENTRY,
        payload: {
          stSize: '123',
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        } as ApiStatEntry,
        tag: 'tag2',
      }),
    ]);

    expect(await harness.collapsibleContainers()).toHaveSize(2);
  }));

  it('shows client id column for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payload: {
          pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
        },
      }),
      newHuntResult({
        clientId: 'C.1234',
        payload: {
          pathspec: {path: 'HKLM\\foo', pathtype: PathSpecPathType.REGISTRY},
        },
      }),
    ]);

    expect(await harness.fileResultsTables()).toHaveSize(1);
    const fileResultsTable = (await harness.fileResultsTables())[0];
    expect(await fileResultsTable.getCellText(0, 'clientId')).toContain(
      'C.1234',
    );
    expect(await harness.registryResultsTables()).toHaveSize(1);
    const registryResultsTable = (await harness.registryResultsTables())[0];
    expect(await registryResultsTable.getCellText(0, 'clientId')).toContain(
      'C.1234',
    );
  }));
});
