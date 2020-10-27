import {async, TestBed, ComponentFixture} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';
import { OsqueryDetails } from './osquery_details';
import { newFlowListEntry, newResultSet } from '@app/lib/models/model_test_util';
import { FlowState, FlowListEntry, FlowResultSet } from '@app/lib/models/flow';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';
import { OsqueryColumn, OsqueryRow } from '@app/lib/api/api_interfaces';
import { DeepMutable } from '@app/lib/type_utils';

initTestEnvironment();

/** Helper class to build a FlowListEntry objects in a declarative manner */
class FlowListEntryBuilder {
  private flowListEntry = newFlowListEntry({args: {query: ''}})  as DeepMutable<FlowListEntry>;

  private stderr = '';
  private table = {
    query: '',
    header: {
      columns: [] as OsqueryColumn[],
    },
    rows: [] as OsqueryRow[],
  };

  withFlowState(state: FlowState): FlowListEntryBuilder {
    this.flowListEntry.flow.state = state;
    return this;
  }

  withQuery(query: string): FlowListEntryBuilder {
    this.setFlowArgsQuery(query);
    this.table.query = query;
    return this;
  }

  withStderr(stderr: string): FlowListEntryBuilder {
    this.stderr = stderr;
    return this;
  }

  withTable(columns: string[], values: string[][]): FlowListEntryBuilder {
    this.table.header.columns = columns.map((colName) => ({name: colName}));
    this.table.rows = values.map((rowValues) => ({values: rowValues}));
    return this;
  }

  build(): FlowListEntry {
    this.includeResultSet();
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

  private includeResultSet(): void {
    const payload = {
      stderr: this.stderr,
      table: this.table,
    }
    this.flowListEntry.resultSets = [
      newResultSet(payload) as DeepMutable<FlowResultSet>,
    ];
  }
}

/** Helper class/data structure to parse and expose all elements of interest from the OsqueryDetails DOM */
class ParsedElements {
  inProgressDiv = this.elementBySelector('.in-progress');
  inProgressText = this.innerText(this.inProgressDiv);

  resultsDiv = this.elementBySelector('.results');

  resultsQueryDiv = this.elementBySelector('.results-query-text');
  resultsQueryText = this.innerText(this.resultsQueryDiv);

  resultsTableColumn = this.elementBySelector('th');
  resultsTableColumnText = this.innerText(this.resultsTableColumn);

  resultsTableCellDiv = this.elementBySelector('td');
  resultsTableCellText = this.innerText(this.resultsTableCellDiv);

  errorDiv = this.elementBySelector('.error');

  stdErrDiv = this.elementBySelector('div', this.errorDiv);
  stdErrText = this.innerText(this.stdErrDiv);

  constructor(private readonly ofFixture: ComponentFixture<OsqueryDetails>) { }

  private elementBySelector(selector: string, root: DebugElement=this.ofFixture.debugElement) {
    return root?.query(By.css(selector));
  }

  private innerText(ofElement: DebugElement) {
    return ofElement?.nativeElement.innerText;
  }
}


describe('osquery-details component', () => {
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

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture);

    expect(parsedElements.resultsDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();

    expect(parsedElements.inProgressDiv).toBeTruthy();
    expect(parsedElements.inProgressText).toEqual(testQuery);
  })

  it('should display only the stderr error if the flow encounters an error', () => {
    const testStderr = 'just a standard err';
    const exptectedText = `stderr is: ${testStderr}`;
    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.ERROR)
      .withStderr(testStderr);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.resultsDiv).toBeFalsy();

    expect(parsedElements.errorDiv).toBeTruthy();
    expect(parsedElements.stdErrDiv).toBeTruthy();
    expect(parsedElements.stdErrText).toEqual(exptectedText);
  })

  it('should display results with the query', () => {
    const testQuery = 'SELECT * FROM users LIMIT 10;';
    const testColName = 'column';
    const testCellValue = 'cell';

    const testFlowListEntry = new FlowListEntryBuilder()
      .withFlowState(FlowState.FINISHED)
      .withTable([testColName], [[testCellValue]])
      .withQuery(testQuery);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedElements(fixture);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();

    expect(parsedElements.resultsDiv).toBeTruthy();

    expect(parsedElements.resultsQueryDiv).toBeTruthy();
    expect(parsedElements.resultsQueryText).toEqual(testQuery);

    expect(parsedElements.resultsTableCellDiv).toBeTruthy();
    expect(parsedElements.resultsTableCellText).toEqual(testCellValue);
  })
});
