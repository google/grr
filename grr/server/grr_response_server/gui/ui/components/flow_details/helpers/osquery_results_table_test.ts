import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {OsqueryTable} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';
import {OsqueryResultsTable} from './osquery_results_table';
import {newOsqueryTable, OsqueryResultsTableDOM} from './osquery_test_util';


initTestEnvironment();


describe('OsqueryResultsTable Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  /**
   * Function that creates a component fixture which is supplied with the
   * OsqueryTable values provided
   */
  function createComponent(osqueryTable: OsqueryTable|null) {
    const fixture = TestBed.createComponent(OsqueryResultsTable);

    fixture.componentInstance.table = osqueryTable;
    fixture.detectChanges();

    return fixture;
  }

  it('should display a table with 5 rows and 5 columns, together with the query',
     () => {
       const rowNumber = 5;
       const columnNumber = 5;
       const query = 'hyd';

       const columns = Array.from<number>({length: columnNumber})
                           .fill(0)
                           .map((i, index) => `Column ${index}`);
       const values =
           Array.from<number>({length: rowNumber}).fill(0).map((value, row) => {
             return Array.from<number>({length: columnNumber})
                 .fill(0)
                 .map((i, col) => `row-${row}, col-${col}`);
           });

       const table = newOsqueryTable(query, columns, values);

       const osqueryResultsTable = createComponent(table).debugElement;
       const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

       expect(parsedTable.errorDiv).toBeFalsy();

       expect(parsedTable?.columnElements?.length).toEqual(columnNumber);
       expect(parsedTable.columnsText).toEqual(columns);

       expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
       expect(parsedTable.cellsText).toEqual(values.flat());

       expect(parsedTable.queryDiv).toBeTruthy();
       expect(parsedTable.queryText).toEqual(query);
     });

  it('should display message if table is not present', () => {
    const osqueryResultsTable = createComponent(null).debugElement;
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable?.columnElements?.length).toBe(0);
    expect(parsedTable?.cellDivs?.length).toBe(0);

    expect(parsedTable.queryDiv).toBeFalsy();

    expect(parsedTable.errorDiv).toBeTruthy();
    expect(parsedTable.errorText).toBe('No rows to display.');
  });

  it('should display message and query if no rows are present', () => {
    const emptyTable = newOsqueryTable('query', [], []);
    const osqueryResultsTable = createComponent(emptyTable).debugElement;
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable?.columnElements?.length).toBe(0);
    expect(parsedTable?.cellDivs?.length).toBe(0);

    expect(parsedTable.queryDiv).toBeTruthy();

    expect(parsedTable.errorDiv).toBeTruthy();
    expect(parsedTable.errorText).toBe('No rows to display.');
  });

  it('should sort results', async () => {
    const rowNumber = 2;
    const columnNumber = 1;

    const columns = Array.from<number>({length: columnNumber})
                        .fill(0)
                        .map((i, index) => `Column ${index}`);
    const values =
        Array.from<number>({length: rowNumber}).fill(0).map((value, row) => {
          return Array.from<number>({length: columnNumber})
              .fill(0)
              .map((i, col) => `row-${row}, col-${col}`);
        });

    const table = newOsqueryTable('', columns, values);

    const fixture = createComponent(table);
    const osqueryResultsTable = fixture.debugElement;
    let parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
    expect(parsedTable.cellsText).toEqual(values.flat());

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const sort = await harnessLoader.getHarness(MatSortHarness);
    // Sort by Path.
    const headers = await sort.getSortHeaders();
    await headers[0].click();  // asc
    await headers[0].click();  // desc

    parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
    expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
    expect(parsedTable.cellsText).toEqual(values.reverse().flat());
  });

  describe('results filtering', () => {
    const rowNumber = 10;
    const columnNumber = 1;
    let columns: ReadonlyArray<string>;
    let values: ReadonlyArray<ReadonlyArray<string>>;
    let table: OsqueryTable;
    let fixture: ComponentFixture<OsqueryResultsTable>;
    let osqueryResultsTable: DebugElement;

    beforeEach(() => {
      columns = Array.from<number>({length: columnNumber})
                    .fill(0)
                    .map((i, index) => `Column ${index}`);
      values =
          Array.from<number>({length: rowNumber}).fill(0).map((value, row) => {
            return Array.from<number>({length: columnNumber})
                .fill(0)
                .map((i, col) => `row-${row}, col-${col}`);
          });

      table = newOsqueryTable('', columns, values);

      fixture = createComponent(table);

      osqueryResultsTable = fixture.debugElement;
    });

    it('starts with all rows displayed', () => {
      const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
      expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
      expect(parsedTable.cellsText).toEqual(values.flat());
    });

    it('filters first row', async () => {
      const filterInput = fixture.debugElement.query(By.css('input'));
      filterInput.nativeElement.value = 'row-0, col-0';
      filterInput.triggerEventHandler(
          'input', {target: filterInput.nativeElement});
      fixture.detectChanges();

      const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
      expect(parsedTable?.cellDivs?.length).toEqual(1);
      expect(parsedTable.cellsText).toEqual(['row-0, col-0']);
    });

    it('filters second row', async () => {
      const filterInput = fixture.debugElement.query(By.css('input'));
      filterInput.nativeElement.value = 'row-1, col-0';
      filterInput.triggerEventHandler(
          'input', {target: filterInput.nativeElement});
      fixture.detectChanges();

      const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
      expect(parsedTable?.cellDivs?.length).toEqual(1);
      expect(parsedTable.cellsText).toEqual(['row-1, col-0']);
    });

    it('filters invalid value, no results', async () => {
      const filterInput = fixture.debugElement.query(By.css('input'));
      filterInput.nativeElement.value = 'invalid';
      filterInput.triggerEventHandler(
          'input', {target: filterInput.nativeElement});
      fixture.detectChanges();

      const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
      expect(parsedTable?.cellDivs?.length).toEqual(1);
      expect(parsedTable.cellsText).toEqual(['No rows to display.']);
    });

    it('no filter, all rows are displayed', async () => {
      const filterInput = fixture.debugElement.query(By.css('input'));
      filterInput.nativeElement.value = '';
      filterInput.triggerEventHandler(
          'input', {target: filterInput.nativeElement});
      fixture.detectChanges();

      const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);
      expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
      expect(parsedTable.cellsText).toEqual(values.flat());
    });
  });

  describe('results pagination', () => {
    const rowNumber = 12;
    const columnNumber = 1;
    let fixture: ComponentFixture<OsqueryResultsTable>;
    let parsedTable: OsqueryResultsTableDOM;
    let paginatorTop: MatPaginatorHarness;
    let paginatorBottom: MatPaginatorHarness;

    beforeEach(async () => {
      const columns = Array.from<number>({length: columnNumber})
                          .fill(0)
                          .map((i, index) => `Column ${index}`);
      const values =
          Array.from<number>({length: rowNumber}).fill(0).map((value, row) => {
            return Array.from<number>({length: columnNumber})
                .fill(0)
                .map((i, col) => `row-${row}, col-${col}`);
          });

      const table = newOsqueryTable('', columns, values);

      fixture = createComponent(table);
      const osqueryResultsTable = fixture.debugElement;
      parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

      const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
      paginatorTop = await harnessLoader.getHarness(
          MatPaginatorHarness.with({selector: '.top-paginator'}));
      paginatorBottom = await harnessLoader.getHarness(
          MatPaginatorHarness.with({selector: '.bottom-paginator'}));
    });

    it('starts with pagesize of 10', async () => {
      // Rows include the header.
      expect(parsedTable?.rowsLength).toBe(11);

      expect(parsedTable.cellsText?.toString()).toContain('row-0');
      expect(parsedTable.cellsText?.toString()).toContain('row-9');
      expect(parsedTable.cellsText?.toString()).not.toContain('row-10');

      expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
      expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    });

    it('paginator forwards updates table contents', async () => {
      // Second page should displays results 11-12
      await paginatorTop.goToNextPage();
      expect(parsedTable.rowsLength).toBe(3);
      expect(await paginatorTop.getRangeLabel()).toBe('11 – 12 of 12');
      expect(await paginatorBottom.getRangeLabel()).toBe('11 – 12 of 12');
      expect(fixture.nativeElement.innerText).not.toContain('row-0');
      expect(fixture.nativeElement.innerText).toContain('row-11');
    });

    it('paginator first page updates table contents', async () => {
      // Start from the second page, then go back.
      await paginatorTop.goToNextPage();
      // First page should displays results 1-10
      await paginatorBottom.goToFirstPage();
      expect(parsedTable.rowsLength).toBe(11);
      expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
      expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
      expect(fixture.nativeElement.innerText).toContain('row-0');
      expect(fixture.nativeElement.innerText).not.toContain('row-11');
    });

    it('paginator increased page size updates table contents', async () => {
      await paginatorTop.setPageSize(50);
      expect(parsedTable.rowsLength).toBe(13);
      expect(await paginatorTop.getPageSize()).toBe(50);
      expect(await paginatorBottom.getPageSize()).toBe(50);
      expect(await paginatorTop.getRangeLabel()).toBe('1 – 12 of 12');
      expect(await paginatorBottom.getRangeLabel()).toBe('1 – 12 of 12');
      expect(fixture.nativeElement.innerText).toContain('row-0');
      expect(fixture.nativeElement.innerText).toContain('row-11');
    });

    it('paginator decreased page size updates table contents', async () => {
      // Start with large page size.
      await paginatorTop.setPageSize(50);
      // Decreased page size should crop results.
      await paginatorBottom.setPageSize(10);
      expect(parsedTable.rowsLength).toBe(11);
      expect(await paginatorTop.getPageSize()).toBe(10);
      expect(await paginatorBottom.getPageSize()).toBe(10);
      expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
      expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
      expect(fixture.nativeElement.innerText).toContain('row-0');
      expect(fixture.nativeElement.innerText).not.toContain('row-11');
    });
  });
});
