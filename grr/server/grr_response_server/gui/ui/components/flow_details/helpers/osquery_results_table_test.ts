import {DebugElement} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {OsqueryTable} from '@app/lib/api/api_interfaces';
import {initTestEnvironment} from '@app/testing';
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

        })
        .compileComponents();
  }));

  /**
   * Function that creates a component fixture which is supplied with the
   * OsqueryTable values provided
   */
  function createElementFrom(osqueryTable?: OsqueryTable): DebugElement {
    const fixture = TestBed.createComponent(OsqueryResultsTable);

    fixture.componentInstance.table = osqueryTable;
    fixture.detectChanges();

    return fixture.debugElement;
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

       const osqueryResultsTable = createElementFrom(table);
       const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

       expect(parsedTable.errorDiv).toBeFalsy();

       expect(parsedTable?.columnElements?.length).toEqual(columnNumber);
       expect(parsedTable.columnsText).toEqual(columns);

       expect(parsedTable?.cellDivs?.length).toEqual(rowNumber * columnNumber);
       expect(parsedTable.cellsText).toEqual(values.flat());

       expect(parsedTable.queryDiv).toBeTruthy();
       expect(parsedTable.queryText).toEqual(query);
     });

  it('should display message if table is not pressent', () => {
    const osqueryResultsTable = createElementFrom(undefined);
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable?.columnElements?.length).toBe(0);
    expect(parsedTable?.cellDivs?.length).toBe(0);

    expect(parsedTable.queryDiv).toBeFalsy();

    expect(parsedTable.errorDiv).toBeTruthy();
    expect(parsedTable.errorText).toBe('No rows to display.');
  });

  it('should display message and query if no rows are pressent', () => {
    const emptyTable = newOsqueryTable('query', [], []);
    const osqueryResultsTable = createElementFrom(emptyTable);
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable?.columnElements?.length).toBe(0);
    expect(parsedTable?.cellDivs?.length).toBe(0);

    expect(parsedTable.queryDiv).toBeTruthy();

    expect(parsedTable.errorDiv).toBeTruthy();
    expect(parsedTable.errorText).toBe('No rows to display.');
  });
});
