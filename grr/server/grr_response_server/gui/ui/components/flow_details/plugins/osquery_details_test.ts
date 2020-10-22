import {async, TestBed, ComponentFixture} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';
import { OsqueryDetails } from './osquery_details';
import { newFlowListEntry, newFlow } from '@app/lib/models/model_test_util';
import { FlowState, FlowListEntry, FlowResultSet, FlowResultSetState } from '@app/lib/models/flow';
import { By } from '@angular/platform-browser';
import { DebugElement, Component } from '@angular/core';
import { OsqueryResult, OsqueryTable } from '@app/lib/api/api_interfaces';


initTestEnvironment();

/** Helper class to build a FlowListEntry objects in a declarative manner */
class FlowListEntryBuilder {
  private flowListEntry = {
    flow: {
      flowId: '',
      clientId: '',
      lastActiveAt: new Date(),
      startedAt: new Date(),
      name: '',
      creator: '',
      args: {
        query: '',
      },
      progress: '',
      state: FlowState.UNSET,
    },
    resultSets: [] as any[],
  }
  private stderr = '';
  private table: any = {
    query: '',
    header: {
      columns: []
    },
    rows: []
  };

  withFlowState(state: FlowState): FlowListEntryBuilder {
    this.flowListEntry.flow.state = state;
    return this;
  }

  withQuery(query: string): FlowListEntryBuilder {
    this.flowListEntry.flow.args.query = query;
    this.table.query = query;
    return this;
  }

  withResult(result: OsqueryResult): FlowListEntryBuilder {
    this.flowListEntry.resultSets = [{
      items: [{
        payload: result,
      }],
    }];
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
    this.flowListEntry.resultSets = [{
      items: [{
        payload: {
          table: this.table,
          stderr: this.stderr,
        }
      }]
    }]
    return this.flowListEntry as FlowListEntry;
  }
}

/** Helper class to parse all elements of interest from the OsqueryDetails DOM */
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

  elementBySelector(selector: string, root: DebugElement=this.ofFixture.debugElement) {
    return root?.query(By.css(selector));
  }

  innerText(ofElement: DebugElement) {
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
