

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {MatProgressSpinnerHarness} from '@angular/material/progress-spinner/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../../../lib/api/http_api_with_translation_test_util';
import {
  newPathSpec,
  newStatEntry,
} from '../../../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../../../testing';
import {
  CollectionState,
  FileResultsTable,
  FlowFileResult,
} from './file_results_table';
import {FileResultsTableHarness} from './testing/file_results_table_harness';

initTestEnvironment();

async function createComponent(
  results: FlowFileResult[],
  isHuntResult = false,
) {
  const fixture = TestBed.createComponent(FileResultsTable);
  fixture.componentRef.setInput('results', results);
  fixture.componentRef.setInput('isHuntResult', isHuntResult);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FileResultsTableHarness,
  );
  return {fixture, harness};
}

describe('File Results Table Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FileResultsTable, NoopAnimationsModule],
      providers: [
        {
          // TODO: Ideally we would use a mock store instead.
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent([]);

    expect(fixture.componentInstance).toBeDefined();
  });

  it('can be created with no rows', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.getRows()).toHaveSize(0);
  }));

  it('renders one stat entry row with correct columns', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          statEntry: newStatEntry({
            pathspec: newPathSpec({path: `/home/foo/bar/0`}),
            stMode: BigInt('420'), // 0644
            stDev: BigInt(`6777220`),
            stNlink: BigInt(`1`),
            stSize: BigInt(`43`),
            stAtime: new Date('2025-01-20T10:00:00.000Z'),
            stMtime: new Date('2025-01-20T11:00:00.000Z'),
            stCtime: new Date('2025-01-20T12:00:00.000Z'),
            stBtime: new Date('2025-01-20T13:00:00.000Z'),
          }),
          clientId: 'C.1234567890',
        },
      ],
      false,
    );

    const table = await harness.table();

    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(9);
    expect(await headerCells[0].getText()).toBe('Type');
    expect(await headerCells[1].getText()).toBe('Path');
    // Misses hashes column as no hashes are provided
    expect(await headerCells[2].getText()).toBe('Mode');
    expect(await headerCells[3].getText()).toBe('Size');
    expect(await headerCells[4].getText()).toContain('Last access time');
    expect(await headerCells[5].getText()).toContain('Last modified time');
    expect(await headerCells[6].getText()).toContain('Last change time');
    expect(await headerCells[7].getText()).toContain('Birth/creation time');
    // Misses Status column as no status is provided
    expect(await headerCells[8].getText()).toBe('Details');

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);

    const pathCells = await rows[0].getCells({columnName: 'path'});
    expect(await pathCells[0].getText()).toContain('/home/foo/bar/0');

    const modeCells = await rows[0].getCells({columnName: 'mode'});
    expect(await modeCells[0].getText()).toContain('-rw-r--r--');

    const sizeCells = await rows[0].getCells({columnName: 'size'});
    expect(await sizeCells[0].getText()).toContain('43 B');

    const atimeCells = await rows[0].getCells({columnName: 'atime'});
    expect(await atimeCells[0].getText()).toContain('2025-01-20 10:00:00 UTC');

    const mtimeCells = await rows[0].getCells({columnName: 'mtime'});
    expect(await mtimeCells[0].getText()).toContain('2025-01-20 11:00:00 UTC');

    const ctimeCells = await rows[0].getCells({columnName: 'ctime'});
    expect(await ctimeCells[0].getText()).toContain('2025-01-20 12:00:00 UTC');

    const btimeCells = await rows[0].getCells({columnName: 'btime'});
    expect(await btimeCells[0].getText()).toContain('2025-01-20 13:00:00 UTC');
  }));

  it('shows a folder icon for directories', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          statEntry: newStatEntry({}),
          clientId: 'C.1234567890',
          isDirectory: true,
        },
      ],
      false,
    );

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const ficonCells = await rows[0].getCells({columnName: 'ficon'});
    expect(await ficonCells[0].getText()).toBe('folder');
  }));

  it('shows an article icon for files', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          statEntry: newStatEntry({}),
          clientId: 'C.1234567890',
          isFile: true,
        },
      ],
      false,
    );

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const ficonCells = await rows[0].getCells({columnName: 'ficon'});
    expect(await ficonCells[0].getText()).toBe('article');
  }));

  it('shows a link icon for symlinks', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          statEntry: newStatEntry({
            stMode: BigInt(0o120644),
          }),
          clientId: 'C.1234567890',
        },
      ],
      false,
    );

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const ficonCells = await rows[0].getCells({columnName: 'ficon'});
    expect(await ficonCells[0].getText()).toBe('link');
  }));

  it('shows a drive file icon for unknown files/directories', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          statEntry: newStatEntry({}),
          clientId: 'C.1234567890',
          // isFile and isDirectory are undefined
        },
      ],
      false,
    );

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const ficonCells = await rows[0].getCells({columnName: 'ficon'});
    expect(await ficonCells[0].getText()).toBe('insert_drive_file');
  }));

  it('includes client id column when isHuntResult is true', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          clientId: 'C.1234567890',
          statEntry: newStatEntry({}),
        },
      ],
      true,
    );

    const table = await harness.table();
    const headers = await table.getHeaderRows();
    const headerCells = await headers[0].getCells();
    expect(headerCells.length).toBe(10);
    expect(await headerCells[0].getText()).toBe('Type');
    expect(await headerCells[1].getText()).toBe('Client ID');
    expect(await headerCells[2].getText()).toBe('Path');
    // Misses hashes column as no hashes are provided
    expect(await headerCells[3].getText()).toBe('Mode');
    expect(await headerCells[4].getText()).toBe('Size');
    expect(await headerCells[5].getText()).toContain('Last access time');
    expect(await headerCells[6].getText()).toContain('Last modified time');
    expect(await headerCells[7].getText()).toContain('Last change time');
    expect(await headerCells[8].getText()).toContain('Birth/creation time');
    // Misses Status column as no status is provided
    expect(await headerCells[9].getText()).toBe('Details');

    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const clientIdCells = await rows[0].getCells({columnName: 'clientId'});
    expect(await clientIdCells[0].getText()).toContain('C.1234567890');
  }));

  it('includes hashes column when hashes are provided', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        hashes: {md5: 'hash'},
        clientId: 'C.1234567890',
      },
    ]);

    const table = await harness.table();
    const headers = await table.getHeaderRows();
    const headerCells = await headers[0].getCells();
    expect(headerCells.length).toBe(10);
    expect(await headerCells[0].getText()).toBe('Type');
    expect(await headerCells[1].getText()).toBe('Path');
    expect(await headerCells[2].getText()).toBe('Hash');
    expect(await headerCells[3].getText()).toBe('Mode');
    expect(await headerCells[4].getText()).toBe('Size');
    expect(await headerCells[5].getText()).toContain('Last access time');
    expect(await headerCells[6].getText()).toContain('Last modified time');
    expect(await headerCells[7].getText()).toContain('Last change time');
    expect(await headerCells[8].getText()).toContain('Birth/creation time');
    // Misses Status column as no status is provided
    expect(await headerCells[9].getText()).toBe('Details');
  }));

  it('renders hashes column content', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        hashes: {md5: 'hash'},
        clientId: 'C.1234567890',
      },
    ]);

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'hashes')).toContain('MD5');
  }));

  it('includes status column when status is provided', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.IN_PROGRESS,
        },
        clientId: 'C.1234567890',
      },
    ]);

    const table = await harness.table();
    const headers = await table.getHeaderRows();
    const headerCells = await headers[0].getCells();
    expect(headerCells.length).toBe(10);
    expect(await headerCells[0].getText()).toBe('Type');
    expect(await headerCells[1].getText()).toBe('Path');
    // Misses hashes column as no hashes are provided
    expect(await headerCells[2].getText()).toBe('Mode');
    expect(await headerCells[3].getText()).toBe('Size');
    expect(await headerCells[4].getText()).toContain('Last access time');
    expect(await headerCells[5].getText()).toContain('Last modified time');
    expect(await headerCells[6].getText()).toContain('Last change time');
    expect(await headerCells[7].getText()).toContain('Birth/creation time');
    expect(await headerCells[8].getText()).toBe('Status');
    expect(await headerCells[9].getText()).toBe('Details');
  }));

  it('renders status column content with progress spinner', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.IN_PROGRESS,
        },
        clientId: 'C.1234567890',
      },
    ]);

    const rows = await harness.getRows();
    const statusCells = await rows[0].getCells({columnName: 'status'});
    expect(
      await statusCells[0].hasHarness(MatProgressSpinnerHarness),
    ).toBeTrue();
  }));

  it('renders status column content with icon', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.WARNING,
        },
        clientId: 'C.1234567890',
      },
    ]);
    const rows = await harness.getRows();
    const statusCell = (await rows[0].getCells({columnName: 'status'}))[0];
    expect(statusCell).toBeDefined();
    expect(await harness.getStatusIconName(0)).toBe('priority_high');
  }));

  it('initially collapses details', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
    ]);

    expect(await harness.isDetailsExpanded(0)).toBeFalse();
  }));

  it('can expand details', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
    ]);

    await harness.toggleDetails(0); // Expand details.

    expect(await harness.isDetailsExpanded(0)).toBeTrue();
  }));

  it('can collapse details', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
    ]);

    await harness.toggleDetails(0); // Expand details.
    await harness.toggleDetails(0); // Collapse details.

    expect(await harness.isDetailsExpanded(0)).toBeFalse();
  }));

  it('expands only one details section at a time', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
    ]);

    await harness.toggleDetails(0); // Expand details.
    await harness.toggleDetails(1); // Expand different details.

    expect(await harness.isDetailsExpanded(0)).toBeFalse();
    expect(await harness.isDetailsExpanded(1)).toBeTrue();
  }));

  it('renders several rows', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({}), clientId: 'C.1234567890'},
    ]);

    expect(await harness.getRows()).toHaveSize(3);
  }));

  it('initialially shows results in provided order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const pathHeader = await sort.getSortHeaders({label: 'Path'});
    expect(await pathHeader[0].getSortDirection()).toBe('');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/0');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/2');
    expect(await harness.getCellText(2, 'path')).toContain('/foo/1');
  }));

  it('can sort ficon column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({
          stMode: BigInt(0o120000), // Symlink.
          pathspec: newPathSpec({path: '/foo/symlink'}),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/folder1'}),
        }),
        clientId: 'C.1234567890',
        isDirectory: true,
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/file'})}),
        clientId: 'C.1234567890',
        isFile: true,
      },
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/folder2'}),
        }),
        clientId: 'C.1234567890',
        isDirectory: true,
      },
    ]);

    const sort = await harness.tableSort();
    const ficonHeader = await sort.getSortHeaders({label: 'Type'});
    await ficonHeader[0].click();

    expect(await ficonHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(4);
    expect(await harness.getCellText(0, 'ficon')).toContain('article');
    expect(await harness.getCellText(0, 'path')).toContain('/foo/file');
    expect(await harness.getCellText(1, 'ficon')).toContain('folder');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/folder1');
    expect(await harness.getCellText(2, 'ficon')).toContain('folder');
    expect(await harness.getCellText(2, 'path')).toContain('/foo/folder2');
    expect(await harness.getCellText(3, 'ficon')).toContain('link');
    expect(await harness.getCellText(3, 'path')).toContain('/foo/symlink');
  }));

  it('can sort path column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const pathHeader = await sort.getSortHeaders({label: 'Path'});
    await pathHeader[0].click();

    expect(await pathHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/0');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/1');
    expect(await harness.getCellText(2, 'path')).toContain('/foo/2');
  }));

  it('can sort size column in descending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {statEntry: newStatEntry({stSize: BigInt(10)}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({stSize: BigInt(20)}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({stSize: BigInt(30)}), clientId: 'C.1234567890'},
    ]);

    const sort = await harness.tableSort();
    const sizeHeader = await sort.getSortHeaders({label: 'Size'});
    await sizeHeader[0].click();
    await sizeHeader[0].click();

    expect(await sizeHeader[0].getSortDirection()).toBe('desc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'size')).toContain('30 B');
    expect(await harness.getCellText(1, 'size')).toContain('20 B');
    expect(await harness.getCellText(2, 'size')).toContain('10 B');
  }));

  it('can sort atime column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const atimeHeader = await sort.getSortHeaders({
      label: /Last access time.*/,
    });
    await atimeHeader[0].click();

    expect(await atimeHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'atime')).toContain(
      '2025-01-20 10:00:00 UTC',
    );
    expect(await harness.getCellText(1, 'atime')).toContain(
      '2025-01-20 11:00:00 UTC',
    );
    expect(await harness.getCellText(2, 'atime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can sort mtime column in descending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const mtimeHeader = await sort.getSortHeaders({
      label: /Last modified time.*/,
    });
    await mtimeHeader[0].click();
    await mtimeHeader[0].click();

    expect(await mtimeHeader[0].getSortDirection()).toBe('desc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'mtime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
    expect(await harness.getCellText(1, 'mtime')).toContain(
      '2025-01-20 11:00:00 UTC',
    );
    expect(await harness.getCellText(2, 'mtime')).toContain(
      '2025-01-20 10:00:00 UTC',
    );
  }));

  it('can sort ctime column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const ctimeHeader = await sort.getSortHeaders({
      label: /Last change time.*/,
    });
    await ctimeHeader[0].click();

    expect(await ctimeHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'ctime')).toContain(
      '2025-01-20 10:00:00 UTC',
    );
    expect(await harness.getCellText(1, 'ctime')).toContain(
      '2025-01-20 11:00:00 UTC',
    );
    expect(await harness.getCellText(2, 'ctime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can sort btime column in descending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const btimeHeader = await sort.getSortHeaders({
      label: /Birth\/creation time.*/,
    });
    await btimeHeader[0].click();
    await btimeHeader[0].click();

    expect(await btimeHeader[0].getSortDirection()).toBe('desc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'btime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
    expect(await harness.getCellText(1, 'btime')).toContain(
      '2025-01-20 11:00:00 UTC',
    );
    expect(await harness.getCellText(2, 'btime')).toContain(
      '2025-01-20 10:00:00 UTC',
    );
  }));

  it('can sort status column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.SUCCESS,
        },
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.ERROR,
        },
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({}),
        status: {
          state: CollectionState.WARNING,
        },
        clientId: 'C.1234567890',
      },
    ]);

    const sort = await harness.tableSort();
    const statusHeader = await sort.getSortHeaders({label: 'Status'});
    await statusHeader[0].click();

    expect(await statusHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getStatusIconName(0)).toBe('check');
    expect(await harness.getStatusIconName(1)).toBe('priority_high');
    expect(await harness.getStatusIconName(2)).toBe('error');
  }));

  it('can filter by file type', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567890',
        isFile: true,
      },
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567891',
        isDirectory: true,
      },
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567892',
        isFile: true,
      },
    ]);

    fixture.componentInstance.dataSource.filter = 'file';

    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'ficon')).toContain('article');
    expect(await harness.getCellText(1, 'ficon')).toContain('article');
  }));

  it('can filter by folder type', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567890',
        isFile: true,
      },
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567891',
        isDirectory: true,
      },
      {
        statEntry: newStatEntry({}),
        clientId: 'C.1234567892',
        isFile: true,
      },
    ]);

    fixture.componentInstance.dataSource.filter = 'folder';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'ficon')).toContain('folder');
  }));

  it('can filter by path', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '/foo/1';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
  }));

  it('can filter by size', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {statEntry: newStatEntry({stSize: BigInt(10)}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({stSize: BigInt(20)}), clientId: 'C.1234567890'},
      {statEntry: newStatEntry({stSize: BigInt(30)}), clientId: 'C.1234567890'},
    ]);

    fixture.componentInstance.dataSource.filter = '20';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'size')).toContain('20 B');
  }));

  it('can filter by atime in milliseconds since epoch', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '1737374400000'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'atime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by atime in UTC string (RFC 7231 format)', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stAtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '20 Jan 2025 12:00:00 GMT'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'atime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by mtime in milliseconds since epoch', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '1737374400000'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'mtime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by mtime in UTC string (RFC 7231 format)', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stMtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '20 Jan 2025 12:00:00 GMT'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'mtime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by ctime in milliseconds since epoch', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '1737374400000'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'ctime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by ctime in UTC string (RFC 7231 format)', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stCtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '20 Jan 2025 12:00:00 GMT'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'ctime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by btime in milliseconds since epoch', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '1737374400000'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'btime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by btime in UTC string (RFC 7231 format)', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T10:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T11:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          stBtime: new Date('2025-01-20T12:00:00.000Z'),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = '20 Jan 2025 12:00:00 GMT'; // 2025-01-20T12:00:00.000Z

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'btime')).toContain(
      '2025-01-20 12:00:00 UTC',
    );
  }));

  it('can filter by mode', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({stMode: BigInt(0o755)}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({stMode: BigInt(0o750)}),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({stMode: BigInt(0o777)}),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = String(0o755);

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'mode')).toContain('-rwxr-xr-x');
  }));

  it('can filter by md5 hash', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        hashes: {md5: 'hash1'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        hashes: {md5: 'hash2'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        hashes: {md5: 'hash3'},
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = 'hash2';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'hashes')).toContain('MD5');
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
  }));

  it('can filter by sha1 hash', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        hashes: {sha1: 'hash1'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        hashes: {sha1: 'hash2'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        hashes: {sha1: 'hash3'},
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = 'hash2';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'hashes')).toContain('SHA-1');
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
  }));

  it('can filter by sha256 hash', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/0'})}),
        hashes: {sha256: 'hash1'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/1'})}),
        hashes: {sha256: 'hash2'},
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({pathspec: newPathSpec({path: '/foo/2'})}),
        hashes: {sha256: 'hash3'},
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentInstance.dataSource.filter = 'hash2';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'hashes')).toContain('SHA-256');
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
  }));

  it('updates the table when the result paths change', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/0'}),
          stSize: BigInt(1),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentRef.setInput('results', [
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/1'}),
          stSize: BigInt(1),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
    expect(await harness.getCellText(0, 'size')).toContain('1');
  }));

  it('updates the table when the number of result paths changes', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/0'}),
          stSize: BigInt(1),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentRef.setInput('results', [
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/0'}),
          stSize: BigInt(2),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/1'}),
          stSize: BigInt(2),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/0');
    expect(await harness.getCellText(0, 'size')).toContain('2');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/1');
    expect(await harness.getCellText(1, 'size')).toContain('2');
  }));

  it('does not update the table when the results change but the paths are the same', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/0'}),
          stSize: BigInt(1),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/1'}),
          stSize: BigInt(1),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    fixture.componentRef.setInput('results', [
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/0'}),
          stSize: BigInt(2),
        }),
        clientId: 'C.1234567890',
      },
      {
        statEntry: newStatEntry({
          pathspec: newPathSpec({path: '/foo/1'}),
          stSize: BigInt(2),
        }),
        clientId: 'C.1234567890',
      },
    ]);

    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/0');
    expect(await harness.getCellText(0, 'size')).toContain('1');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/1');
    expect(await harness.getCellText(1, 'size')).toContain('1');
  }));
});
