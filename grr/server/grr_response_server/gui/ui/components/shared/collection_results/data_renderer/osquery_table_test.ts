

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {OsqueryTable, OsqueryTableData} from './osquery_table';
import {OsqueryTableHarness} from './testing/osquery_table_harness';

initTestEnvironment();

async function createComponent(table: OsqueryTableData, isHuntResult = false) {
  const fixture = TestBed.createComponent(OsqueryTable);
  fixture.componentRef.setInput('tableData', table);
  fixture.componentRef.setInput('isHuntResult', isHuntResult);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OsqueryTableHarness,
  );
  return {fixture, harness};
}

describe('Osquery Table Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [OsqueryTable, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent({});

    expect(fixture.componentInstance).toBeDefined();
  });

  it('displays the query', async () => {
    const {harness} = await createComponent({
      query: 'SELECT * FROM test_table\nWHERE column = "FOO"',
    });
    const query = await harness.queryCodeblock();
    expect(await query.linesText()).toEqual([
      'SELECT * FROM test_table',
      'WHERE column = "FOO"',
    ]);
  });

  it('displays empty table if no rows are present', async () => {
    const {harness} = await createComponent({
      rows: [],
    });
    const table = await harness.table();
    const rows = await table.getFooterRows();
    expect(rows.length).toBe(0);
    // TODO: Add check if "No rows to display." is displayed. The
    // row is currently not returned by the MatTableHarness.
  });

  it('displays all column names', async () => {
    const {harness} = await createComponent({
      header: {
        columns: [{name: 'Column 0'}, {name: 'Column 1'}, {name: 'Column 2'}],
      },
      rows: [
        {
          clientId: 'C.1234567890',
          values: ['Value 0', 'Value 1', 'Value 2'],
        },
      ],
    });
    const table = await harness.table();
    const headerRows = await table.getHeaderRows();
    const headerCells = await headerRows[0].getCells();
    const headerTexts = await Promise.all(
      headerCells.map((cell) => cell.getText()),
    );
    expect(headerTexts).toEqual(['Column 0', 'Column 1', 'Column 2']);
  });

  it('displays client id column for hunt results', async () => {
    const {harness} = await createComponent(
      {
        header: {
          columns: [{name: 'Column'}],
        },
        rows: [
          {
            clientId: 'C.1234567890',
            values: ['Value'],
          },
        ],
      },
      true,
    );
    const table = await harness.table();
    const headerRows = await table.getHeaderRows();
    const headerCells = await headerRows[0].getCells();
    const headerTexts = await Promise.all(
      headerCells.map((cell) => cell.getText()),
    );
    expect(headerTexts).toEqual(['Client ID', 'Column']);
    const rows = await harness.getRows();
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts[0]).toContain('C.1234567890');
    expect(cellTexts[1]).toContain('Value');
  });

  it('displays a single row', async () => {
    const {harness} = await createComponent({
      header: {
        columns: [{name: 'Column 0'}, {name: 'Column 1'}, {name: 'Column 2'}],
      },
      rows: [
        {
          clientId: 'C.1234567890',
          values: ['Value 0', 'Value 1', 'Value 2'],
        },
      ],
    });
    const table = await harness.table();
    const rows = await table.getRows();
    expect(rows.length).toBe(1);
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts).toEqual(['Value 0', 'Value 1', 'Value 2']);
  });

  it('displays multiple rows', async () => {
    const {harness} = await createComponent({
      header: {
        columns: [{name: 'Column 0'}, {name: 'Column 1'}, {name: 'Column 2'}],
      },
      rows: [
        {
          clientId: 'C.1234567890',
          values: ['Value 0', 'Value 1', 'Value 2'],
        },
        {
          clientId: 'C.1234567891',
          values: ['Value 3', 'Value 4', 'Value 5'],
        },
      ],
    });
    const table = await harness.table();
    const rows = await table.getRows();
    expect(rows.length).toBe(2);
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts).toEqual(['Value 0', 'Value 1', 'Value 2']);
    const cells2 = await rows[1].getCells();
    const cellTexts2 = await Promise.all(cells2.map((cell) => cell.getText()));
    expect(cellTexts2).toEqual(['Value 3', 'Value 4', 'Value 5']);
  });

  it('sorts results', async () => {
    const {harness} = await createComponent({
      header: {
        columns: [{name: 'Column0'}, {name: 'Column1'}],
      },
      rows: [
        {
          clientId: 'C.1234567890',
          values: ['BBB 1', 'BBB 2'],
        },
        {
          clientId: 'C.1234567891',
          values: ['AAA 1', 'AAA 2'],
        },
      ],
    });
    const tableSort = await harness.tableSort();
    const headers = await tableSort.getSortHeaders();
    await headers[0].click(); // asc
    expect(await headers[0].getSortDirection()).toBe('asc');
    const rows = await harness.getRows();
    const cells0 = await rows[0].getCells();
    const cellTexts0 = await Promise.all(cells0.map((cell) => cell.getText()));
    expect(cellTexts0).toEqual(['AAA 1', 'AAA 2']);
    const cells1 = await rows[1].getCells();
    const cellTexts1 = await Promise.all(cells1.map((cell) => cell.getText()));
    expect(cellTexts1).toEqual(['BBB 1', 'BBB 2']);
  });

  it('filters results', async () => {
    const {harness} = await createComponent({
      header: {
        columns: [{name: 'Column0'}, {name: 'Column1'}],
      },
      rows: [
        {
          clientId: 'C.1234567890',
          values: ['BBB 1', 'BBB 2'],
        },
        {
          clientId: 'C.1234567891',
          values: ['AAA 1', 'AAA 2'],
        },
      ],
    });
    const filterPaginate = await harness.filterPaginate();
    const filterInput = await filterPaginate.filterInput();
    await filterInput.setValue('BBB 1');
    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts).toEqual(['BBB 1', 'BBB 2']);
  });
});
