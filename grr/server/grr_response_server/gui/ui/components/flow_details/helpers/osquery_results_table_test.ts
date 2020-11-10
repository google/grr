import { TestBed, async } from '@angular/core/testing';
import { HelpersModule } from './module';
import { DebugElement } from '@angular/core';
import { OsqueryResultsTable } from './osquery_results_table';
import { By } from '@angular/platform-browser';
import { OsqueryTable } from '@app/lib/api/api_interfaces';
import { newOsqueryTable } from '@app/lib/models/model_test_util';

/** Helper data structure to parse an osquery_results_table */
class OsqueryResultsTableDOM {
  readonly queryDiv = this.rootElement.query(By.css('.results-query-text'));
  readonly queryText = this.queryDiv?.nativeElement.innerText;

  readonly columnElements = this.rootElement.queryAll(By.css('th'));
  readonly columnsText = this.columnElements.map(columnElement => columnElement.nativeElement.innerText);

  readonly cellDivs = this.rootElement.queryAll(By.css('td'));
  readonly cellsText = this.cellDivs.map(cellDiv => cellDiv.nativeElement.innerText);

  readonly errorDiv = this.rootElement.query(By.css('.error'));
  readonly errorText = this.errorDiv?.nativeElement.innerText;

  constructor(private readonly rootElement: DebugElement) { }
}

describe('OsqueryResultsTable Component', () => {
  beforeEach(async(() => {
    TestBed
      .configureTestingModule({
        imports: [
          HelpersModule,
        ],
      })
      .compileComponents();
  }));

  /**
   * Function that creates a component fixture which is supplied with the
   * OsqueryTable values provided
   */
  function createElementFrom(osqueryTable?: OsqueryTable)
    : DebugElement {
    const fixture = TestBed.createComponent(OsqueryResultsTable);

    fixture.componentInstance.table = osqueryTable;
    fixture.detectChanges();

    return fixture.debugElement;
  }

  it('should display a table with 5 rows and 5 columns, together with the query', () => {
    const rowNumber = 5;
    const columnNumber = 5;
    const query = 'hyd';

    const columns = Array(columnNumber).fill(0).map((_, index) => `Column ${index}`);
    const values = Array(rowNumber).fill(0).map((_, row) => {
      return Array(columnNumber).fill(0).map((_2, col) => `row-${row}, col-${col}`);
    });

    const table = newOsqueryTable(query, columns, values);

    const osqueryResultsTable = createElementFrom(table);
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable.errorDiv).toBeFalsy();

    expect(parsedTable.columnElements.length).toEqual(columnNumber);
    expect(parsedTable.columnsText).toEqual(columns);

    expect(parsedTable.cellDivs.length).toEqual(rowNumber * columnNumber);
    expect(parsedTable.cellsText).toEqual(values.flat());

    expect(parsedTable.queryDiv).toBeTruthy();
    expect(parsedTable.queryText).toEqual(query);
  });

  it('should display message if table is not pressent', () => {
    const osqueryResultsTable = createElementFrom(undefined);
    const parsedTable = new OsqueryResultsTableDOM(osqueryResultsTable);

    expect(parsedTable.columnElements.length).toBe(0);
    expect(parsedTable.cellDivs.length).toBe(0);
    expect(parsedTable.queryDiv).toBeFalsy();

    expect(parsedTable.errorDiv).toBeTruthy();
    expect(parsedTable.errorText).toBe('No table to display.');
  })
});
