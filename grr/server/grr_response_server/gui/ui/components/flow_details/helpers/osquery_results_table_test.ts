import { TestBed, async } from '@angular/core/testing';
import { HelpersModule } from './module';
import { OsqueryTableBuilder, ParsedDetailsTable } from './osquery_test_utils';
import { DebugElement } from '@angular/core';
import { OsqueryResultsTable } from './osquery_results_table';

fdescribe('OsqueryResultsTable Component', () => {
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
   * OsqueryTable values provided by the builder
   */
  function createElementFrom(osqueryTableBuilder: OsqueryTableBuilder)
    : DebugElement {
    const fixture = TestBed.createComponent(OsqueryResultsTable);

    fixture.componentInstance.tableToDisplay = osqueryTableBuilder.build();
    fixture.detectChanges();

    return fixture.debugElement;
  }

  it('should display a table with 5 rows and 5 columns', () => {
    const rowNumber = 5;
    const columnNumber = 5;

    const columns = Array(columnNumber).fill(0).map((_v, index) => `Column ${index}`);
    const values = Array(rowNumber).fill(0).map((_v1, row) => {
      return Array(columnNumber).fill(0).map((_v2, col) => `row-${row}, col-${col}`);
    });

    const tableBuilder = new OsqueryTableBuilder()
      .withColumns(columns)
      .withValues(values);

    const osqueryResultsTable = createElementFrom(tableBuilder);
    const parsedTable = new ParsedDetailsTable(osqueryResultsTable);

    expect(parsedTable.columnElements.length).toEqual(columnNumber);
    expect(parsedTable.columnsText).toEqual(columns);

    expect(parsedTable.cellDivs.length).toEqual(rowNumber * columnNumber);
    expect(parsedTable.cellsText).toEqual(values.flat());
  });

  it('should display query text', () => {
    const query = 'hyd';

    const tableBuilder = new OsqueryTableBuilder()
      .withQuery(query);

    const osqueryResultsTable = createElementFrom(tableBuilder);
    const parsedTable = new ParsedDetailsTable(osqueryResultsTable);

    expect(parsedTable.queryDiv).toBeTruthy();
    expect(parsedTable.queryText).toEqual(query);
  })
});
