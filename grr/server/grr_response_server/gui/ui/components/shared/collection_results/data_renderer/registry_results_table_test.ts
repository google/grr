

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {RegistryType} from '../../../../lib/models/flow';
import {initTestEnvironment} from '../../../../testing';
import {
  RegistryKeyWithClientId,
  RegistryResultsTable,
  RegistryValueWithClientId,
} from './registry_results_table';
import {RegistryResultsTableHarness} from './testing/registry_results_table_harness';

initTestEnvironment();

async function createComponent(
  results: Array<RegistryKeyWithClientId | RegistryValueWithClientId>,
  isHuntResult = false,
) {
  const fixture = TestBed.createComponent(RegistryResultsTable);
  fixture.componentRef.setInput('results', results);
  fixture.componentRef.setInput('isHuntResult', isHuntResult);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    RegistryResultsTableHarness,
  );
  return {fixture, harness};
}

describe('Registry Results Table Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [RegistryResultsTable, NoopAnimationsModule],
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

  it('renders one RegistryKey row with correct columns', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/bar',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
    ]);

    const table = await harness.table();

    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(3);
    expect(await headerCells[0].getText()).toBe('');
    expect(await headerCells[1].getText()).toBe('Path');
    expect(await headerCells[2].getText()).toBe('Type');

    const rows = await table.getRows();
    expect(rows.length).toBe(1);

    const pathCells = await rows[0].getCells({columnName: 'path'});
    expect(await pathCells[0].getText()).toContain('/foo/bar');

    const typeCells = await rows[0].getCells({columnName: 'type'});
    expect(await typeCells[0].getText()).toContain('REG_KEY');
  }));

  it('includes client id column for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          path: '/foo/bar',
          type: RegistryType.REG_NONE,
          value: {
            integer: '123',
          },
          clientId: 'C.1234',
        } as RegistryValueWithClientId,
      ],
      true,
    );

    const table = await harness.table();
    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(5);
    expect(await headerCells[0].getText()).toBe('');
    expect(await headerCells[1].getText()).toBe('Client ID');
    expect(await headerCells[2].getText()).toBe('Path');
    expect(await headerCells[3].getText()).toBe('Type');
    expect(await headerCells[4].getText()).toBe('Value');
    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
    expect(await harness.getCellText(0, 'path')).toContain('/foo/bar');
    expect(await harness.getCellText(0, 'type')).toContain('REG_NONE');
    expect(await harness.getCellText(0, 'value')).toContain('123');
  }));

  it('includes size column when RegistryValue is provided', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/bar',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    const table = await harness.table();
    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(4);
    expect(await headerCells[0].getText()).toBe('');
    expect(await headerCells[1].getText()).toBe('Path');
    expect(await headerCells[2].getText()).toBe('Type');
    expect(await headerCells[3].getText()).toBe('Value');
    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/bar');
    expect(await harness.getCellText(0, 'type')).toContain('REG_NONE');
    expect(await harness.getCellText(0, 'value')).toContain('123');
  }));

  it('renders all column header when both RegistryKey and RegistryValue are present', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/baz',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/bar',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    const table = await harness.table();
    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(4);
    expect(await headerCells[0].getText()).toBe('');
    expect(await headerCells[1].getText()).toBe('Path');
    expect(await headerCells[2].getText()).toBe('Type');
    expect(await headerCells[3].getText()).toBe('Value');
  }));

  it('renders multiple rows with RegistryKeys and RegistryValues', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/baz',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/bar',
        type: RegistryType.REG_NONE,
        value: {
          string: 'foo-baz-123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/baz');
    expect(await harness.getCellText(0, 'type')).toContain('REG_KEY');
    expect(await harness.getCellText(0, 'value')).toBe('');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/bar');
    expect(await harness.getCellText(1, 'type')).toContain('REG_NONE');
    expect(await harness.getCellText(1, 'value')).toContain('foo-baz-123');
  }));

  it('initialially shows results in provided order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/2',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/0',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
      {
        path: '/foo/1',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
    ]);

    const sort = await harness.tableSort();
    const pathHeader = await sort.getSortHeaders({label: 'Path'});
    expect(await pathHeader[0].getSortDirection()).toBe('');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/2');
    expect(await harness.getCellText(1, 'path')).toContain('/foo/0');
    expect(await harness.getCellText(2, 'path')).toContain('/foo/1');
  }));

  it('can sort client id column in ascending order for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent(
      [
        {
          path: '/foo/2',
          type: 'REG_KEY',
          clientId: 'C.1234',
        } as RegistryKeyWithClientId,
        {
          path: '/foo/0',
          type: RegistryType.REG_NONE,
          value: {
            integer: '123',
          },
          clientId: 'C.3456',
        } as RegistryValueWithClientId,
        {
          path: '/foo/1',
          type: 'REG_KEY',
          clientId: 'C.2345',
        } as RegistryKeyWithClientId,
      ],
      true,
    );

    const sort = await harness.tableSort();
    const clientIdHeader = await sort.getSortHeaders({label: 'Client ID'});
    await clientIdHeader[0].click();

    expect(await clientIdHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
    expect(await harness.getCellText(1, 'clientId')).toContain('C.2345');
    expect(await harness.getCellText(2, 'clientId')).toContain('C.3456');
  }));

  it('can sort path column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/2',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/0',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
      {
        path: '/foo/1',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
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

  it('can sort type column in ascending order', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        path: '/foo/2',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/0',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
      {
        path: '/foo/1',
        type: RegistryType.REG_SZ,
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    const sort = await harness.tableSort();
    const typeHeader = await sort.getSortHeaders({label: 'Type'});
    await typeHeader[0].click();

    expect(await typeHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'type')).toContain('REG_KEY');
    expect(await harness.getCellText(1, 'type')).toContain('REG_NONE');
    expect(await harness.getCellText(2, 'type')).toContain('REG_SZ');
  }));

  it('can filter by client id for hunt results', fakeAsync(async () => {
    const {harness, fixture} = await createComponent(
      [
        {
          path: '/foo/2',
          type: 'REG_KEY',
          clientId: 'C.1234',
        } as RegistryKeyWithClientId,
        {
          path: '/foo/0',
          type: RegistryType.REG_NONE,
          value: {
            integer: '123',
          },
          clientId: 'C.2345',
        } as RegistryValueWithClientId,
        {
          path: '/foo/1',
          type: RegistryType.REG_SZ,
          value: {
            integer: '123',
          },
          clientId: 'C.3456',
        } as RegistryValueWithClientId,
      ],
      true,
    );

    fixture.componentInstance.dataSource.filter = '2345';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('2345');
  }));

  it('can filter by path', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        path: '/foo/2',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/0',
        type: RegistryType.REG_NONE,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
      {
        path: '/foo/1',
        type: RegistryType.REG_SZ,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    fixture.componentInstance.dataSource.filter = '/foo/1';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'path')).toContain('/foo/1');
  }));

  it('can filter by type', fakeAsync(async () => {
    const {harness, fixture} = await createComponent([
      {
        path: '/foo/2',
        type: 'REG_KEY',
        clientId: 'C.1234',
      } as RegistryKeyWithClientId,
      {
        path: '/foo/0',
        type: RegistryType.REG_NONE,
        value: {
          integer: '456',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
      {
        path: '/foo/1',
        type: RegistryType.REG_SZ,
        value: {
          integer: '123',
        },
        clientId: 'C.1234',
      } as RegistryValueWithClientId,
    ]);

    fixture.componentInstance.dataSource.filter = 'REG_SZ';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'type')).toContain('REG_SZ');
  }));
});
