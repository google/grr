import {async, TestBed, ComponentFixture} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';
import { OsqueryDetails } from './osquery_details';
import { newFlowListEntry, newFlowResultSet } from '@app/lib/models/model_test_util';
import { FlowState, FlowListEntry, FlowResultSet } from '@app/lib/models/flow';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';
import { OsqueryColumn, OsqueryRow, OsqueryTable } from '@app/lib/api/api_interfaces';
import { DeepMutable } from '@app/lib/type_utils';

initTestEnvironment();

type MyOsqueryTable = {
  query: string,
  header: {
    columns: ReadonlyArray<OsqueryColumn>,
  },
  rows: ReadonlyArray<OsqueryRow>
};

function newOsqueryTable(): MyOsqueryTable {
  return {
    query: '',
    header: {
      columns: [] as ReadonlyArray<OsqueryColumn>,
    },
    rows: [] as ReadonlyArray<OsqueryRow>,
  };
}

/** Helper class to build a FlowListEntry objects in a declarative manner */
class FlowListEntryBuilder {
  private flowListEntry = newFlowListEntry({args: {query: ''}})  as DeepMutable<FlowListEntry>;

  private query = '';

  private stderr = '';
  private resultsTable?: MyOsqueryTable;

  private progressRowsCount = 0;
  private progressTable?: MyOsqueryTable;

  withFlowState(state: FlowState): FlowListEntryBuilder {
    this.flowListEntry.flow.state = state;
    return this;
  }

  withQuery(query: string): FlowListEntryBuilder {
    this.query = query;
    return this;
  }

  withStderr(stderr: string): FlowListEntryBuilder {
    this.stderr = stderr;
    return this;
  }

  withResultsTable(columns: ReadonlyArray<string>, values: ReadonlyArray<ReadonlyArray<string>>): FlowListEntryBuilder {
    this.resultsTable = newOsqueryTable();
    this.setTableValuesTo(this.resultsTable, columns, values);
    return this;
  }

  withProgressTable(columns: ReadonlyArray<string>, values: ReadonlyArray<ReadonlyArray<string>>): FlowListEntryBuilder {
    this.progressTable = newOsqueryTable();
    this.setTableValuesTo(this.progressTable, columns, values);
    return this;
  }

  withProgressRowsCount(count: number): FlowListEntryBuilder {
    this.progressRowsCount = count;
    return this;
  }

  build(): FlowListEntry {
    this.includeResultSet();
    this.includeProgress();
    this.setFlowArgsQuery(this.query);
    return this.flowListEntry as FlowListEntry;
  }

  private setFlowArgsQuery(query: string): void {
    if (this.flowListEntry.flow.args instanceof Object) {
      this.flowListEntry.flow.args = {
        ...this.flowListEntry.flow.args,
        query,
      };
    } else {
      this.flowListEntry.flow.args = { query };
    }
  }

  private setTableValuesTo(
    table: MyOsqueryTable,
    columns: ReadonlyArray<string>,
    values: ReadonlyArray<ReadonlyArray<string>>
  ): void {
    table.header.columns = columns.map((colName) => ({name: colName}));
    table.rows = values.map((rowValues) => ({values: rowValues}));
  }

  private includeResultSet(): void {
    const payload = {
      stderr: this.stderr,
      table: this.tableWithQuery(this.resultsTable),
    }
    this.flowListEntry.resultSets = [
      newFlowResultSet(payload) as DeepMutable<FlowResultSet>,
    ];
  }

  private includeProgress(): void {
    const progress = {
      totalRowsCount: this.progressRowsCount,
      partialTable: this.tableWithQuery(this.progressTable),
    };
    this.flowListEntry.flow.progress = progress;
  }

  private tableWithQuery(table: MyOsqueryTable | undefined): MyOsqueryTable | undefined {
    if (table) {
      return {
        ...table,
        query: this.query,
      }
    } else {
      return table;
    }
  }
}

function elementBySelector(selector: string, root: DebugElement): DebugElement {
  return root?.query(By.css(selector));
}

function manyElementsBySelector(selector: string, root: DebugElement): DebugElement[] {
  return root?.queryAll(By.css(selector));
}

function innerText(ofElement: DebugElement) {
  return ofElement?.nativeElement.innerText;
}

/** Helper data structure to parse an osquery_results_table */
class ParsedTable {
  queryDiv = elementBySelector('.results-query-text', this.rootElement);
  queryText = innerText(this.queryDiv);

  columnElements = manyElementsBySelector('th', this.rootElement);
  columnsText = this.columnElements.map(columnElement => innerText(columnElement));

  cellDivs = manyElementsBySelector('td', this.rootElement);
  cellsText = this.cellDivs.map(cellDiv => innerText(cellDiv));

  private constructor(private readonly rootElement: DebugElement) { }

  static fromElement(element: DebugElement): ParsedTable | null {
    return element ? new ParsedTable(element) : null;
  }
}

/** Helper data structure to parse and expose all elements of interest from the OsqueryDetails DOM */
class ParsedElements {
  inProgressDiv = elementBySelector('.in-progress', this.rootElement);
  inProgressText = innerText(this.inProgressDiv);

  errorDiv = elementBySelector('.error', this.rootElement);
  stdErrDiv = elementBySelector('div', this.errorDiv);
  stdErrText = innerText(this.stdErrDiv);

  resultsDiv = elementBySelector('.results-table', this.rootElement);
  resultsTable = ParsedTable.fromElement(this.resultsDiv);

  progressDiv = elementBySelector('.progress-table', this.rootElement);
  progressTable = ParsedTable.fromElement(this.progressDiv);

  showAdditionalDiv = elementBySelector('.show-additional', this.progressDiv);
  showAdditionalButton = elementBySelector('button', this.showAdditionalDiv);
  showAdditionalText = elementBySelector('.show-additional-text', this.showAdditionalDiv);

  constructor(private readonly rootElement: DebugElement) { }
}

fdescribe('osquery-details component', () => {
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],

          providers: []
        })
        .compileComponents();
  }));

  /**
   * Function that creates a component fixture which is supplied with
   * FlowListEntry values provided by the builder
   */
  function createFixtureFrom(flowListEntryBuilder: FlowListEntryBuilder)
    : ComponentFixture<OsqueryDetails> {
    const fixture = TestBed.createComponent(OsqueryDetails);
    fixture.componentInstance.flowListEntry = flowListEntryBuilder.build();
    fixture.detectChanges();

    return fixture;
  }

  it('should display only the query argument when flow is still running', () => {
    const testQuery = 'SELECT * FROM users LIMIT 10;';
    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.RUNNING)
      .withQuery(testQuery);
    const expectedQueryText = `Query in progress: ${testQuery}`;

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture.debugElement);

    expect(parsedElements.resultsTable).toBeFalsy();
    expect(parsedElements.progressTable).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();

    expect(parsedElements.inProgressDiv).toBeTruthy();
    expect(parsedElements.inProgressText).toEqual(expectedQueryText);
  });

  it('should display only the stderr error if the flow encounters an error', () => {
    const testStderr = 'just a standard err';
    const exptectedText = `stderr is: ${testStderr}`;
    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.ERROR)
      .withStderr(testStderr);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.resultsTable).toBeFalsy();
    expect(parsedElements.progressTable).toBeFalsy();

    expect(parsedElements.errorDiv).toBeTruthy();
    expect(parsedElements.stdErrDiv).toBeTruthy();
    expect(parsedElements.stdErrText).toEqual(exptectedText);
  });

  fit('should display progress table with no "show additional" section if results are not truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.FINISHED)
      .withProgressTable([testColName], [[testCellValue]])
      .withProgressRowsCount(1)
      .withQuery(testQuery);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTable).toBeFalsy();

    expect(parsedElements.progressTable).toBeTruthy();
    // expect(parsedElements.progressTable?.columnsText).toEqual([testColName]);
    // expect(parsedElements.progressTable?.cellsText).toEqual([testCellValue]);

    expect(parsedElements.showAdditionalDiv).toBeFalsy();
  });

  fit('should display progress table, correct label and a button to request more if results are truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.FINISHED)
      .withProgressTable([testColName], [[testCellValue]])
      .withProgressRowsCount(2) // This is more than the number of rows in the progress table (1)
      .withQuery(testQuery);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTable).toBeFalsy();

    expect(parsedElements.progressTable).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeFalsy();
    expect(parsedElements.)
  })
});
