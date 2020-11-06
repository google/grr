import { async, TestBed, ComponentFixture} from '@angular/core/testing';
import { initTestEnvironment } from '@app/testing';

import { PluginsModule } from './module';
import { OsqueryDetails } from './osquery_details';
import { FlowState, FlowListEntry } from '@app/lib/models/flow';
import { DebugElement } from '@angular/core';
import { By } from '@angular/platform-browser';
import { newFlowListEntry, newFlowResultSet, newFlow } from '@app/lib/models/model_test_util';

initTestEnvironment();

/**
 * Builds an OsqueryTable
 * @param query The Osquery query which produced this table
 * @param columns Column names of the table
 * @param rows Array of arrays containing row values
 */
export function newOsqueryTable(
  query: string,
  columns: ReadonlyArray<string>,
  rows: ReadonlyArray<ReadonlyArray<string>>,
) {
  return {
    query,
    header: {
      columns: columns.map(colName => ({name: colName})),
    },
    rows: rows.map(rowValues => ({values: rowValues})),
  };
}

/** Helper data structure to parse and expose all elements of interest from the OsqueryDetails DOM */
class OsqueryDetailsDOM {
  inProgressDiv = this.rootElement?.query(By.css('.in-progress'));
  inProgressText = this.inProgressDiv?.nativeElement.innerText;

  errorDiv = this.rootElement?.query(By.css('.error'));
  stdErrDiv = this.errorDiv?.query(By.css('div'));
  stdErrText = this.stdErrDiv?.nativeElement.innerText;

  resultsTableDiv = this.rootElement.query(By.css('.results-table'));

  progressTableDiv = this.rootElement.query(By.css('.progress-table'));

  showAdditionalDiv = this.progressTableDiv?.query(By.css('.show-additional'));
  showAdditionalButton = this.showAdditionalDiv?.query(By.css('button'));
  showAdditionalButtonText = this.showAdditionalButton?.nativeElement.textContent;

  errorAdditionalDiv = this.rootElement.query(By.css('.error-show-additional'));

  errorAdditionalSpan = this.errorAdditionalDiv?.query(By.css('span'));
  errorAdditionalSpanText = this.errorAdditionalSpan?.nativeElement.innerText;

  errorAdditionalButton = this.errorAdditionalDiv?.query(By.css('button'));
  errorAdditionalButtonText = this.errorAdditionalButton?.nativeElement.textContent;

  constructor(private readonly rootElement: DebugElement) { }
}

/**
 * Function that creates a component fixture which is supplied with the
 * FlowListEntry value provided
 */
function createFixtureFrom(flowListEntry: FlowListEntry)
  : ComponentFixture<OsqueryDetails> {
  const fixture = TestBed.createComponent(OsqueryDetails);
  fixture.componentInstance.flowListEntry = flowListEntry;
  fixture.detectChanges();

  return fixture;
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

  it('should display only the query argument when flow is still running', () => {
    const testQuery = 'SELECT * FROM users LIMIT 10;';
    const testFlowListEntry = newFlowListEntry({
      state: FlowState.RUNNING,
      args: {
        query: testQuery,
      },
    });

    const expectedQueryText = `Query in progress: ${testQuery}`;

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.progressTableDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.showAdditionalDiv).toBeFalsy();
    expect(parsedElements.errorAdditionalDiv).toBeFalsy();

    expect(parsedElements.inProgressDiv).toBeTruthy();
    expect(parsedElements.inProgressText).toEqual(expectedQueryText);
  });

  it('should display only the stderr error if the flow encounters an error', () => {
    const testStderr = 'just a standard err';
    const exptectedText = `stderr is: ${testStderr}`;

    const testFlowListEntry = {
      flow: newFlow({
        state: FlowState.ERROR,
      }),
      resultSets: [
        newFlowResultSet({
          stderr: testStderr,
        }),
      ],
    };

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.progressTableDiv).toBeFalsy();
    expect(parsedElements.showAdditionalDiv).toBeFalsy();
    expect(parsedElements.errorAdditionalDiv).toBeFalsy();

    expect(parsedElements.errorDiv).toBeTruthy();
    expect(parsedElements.stdErrDiv).toBeTruthy();
    expect(parsedElements.stdErrText).toEqual(exptectedText);
  });

  it('should display progress table with no "show additional" section if results are not truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = newFlowListEntry({
      state: FlowState.FINISHED,
      progress: {
        partialTable: newOsqueryTable(testQuery, [testColName], [[testCellValue]]),
        totalRowCount: 1, // Not more than the number of rows in the progress table (1),
      },
      args: {
        query: testQuery,
      }
    });

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.errorAdditionalDiv).toBeFalsy();

    expect(parsedElements.progressTableDiv).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeFalsy();
  });

  it('should display progress table, and a button with count to request more if results are truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = newFlowListEntry({
      state: FlowState.FINISHED,
      progress: {
        partialTable: newOsqueryTable(testQuery, [testColName], [[testCellValue]]),
        totalRowCount: 2, // More than the number of rows in the progress table (1),
      },
      args: {
        query: testQuery,
      }
    });

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.errorAdditionalDiv).toBeFalsy();

    expect(parsedElements.progressTableDiv).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeTruthy();
    expect(parsedElements.showAdditionalButton).toBeTruthy();
    expect(parsedElements.showAdditionalButtonText).toBe('View all rows (1 more)');
  });

  it('shouldn\'t display the show-additional section if flow is still in progress', () => {
    const testQuery = 'grr?';
    const testFlowListEntry = newFlowListEntry({
      state: FlowState.RUNNING,
      args: {
        query: testQuery,
      }
    });

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.showAdditionalDiv).toBeFalsy();
  });

  it('should display error-show-additional section if result and progress are undefined (for some reason)', () => {
    const testFlowListEntry = newFlowListEntry({
      state: FlowState.FINISHED,
    });

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.errorAdditionalDiv).toBeTruthy();
    expect(parsedElements.errorAdditionalSpan).toBeTruthy();
    expect(parsedElements.errorAdditionalSpanText).toBe('Results might be missing or incomplete.');
    expect(parsedElements.errorAdditionalButton).toBeTruthy();
    expect(parsedElements.errorAdditionalButtonText).toBe('Try requesting the full table');
  });
});
