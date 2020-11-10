import { async, TestBed, ComponentFixture} from '@angular/core/testing';
import { initTestEnvironment } from '@app/testing';

import { PluginsModule } from './module';
import { OsqueryDetails } from './osquery_details';
import { FlowState, FlowListEntry } from '@app/lib/models/flow';
import { DebugElement } from '@angular/core';
import { By } from '@angular/platform-browser';
import { newFlowListEntry, newFlowResultSet, newFlow } from '@app/lib/models/model_test_util';
import { OsqueryResultsTableDOM, newOsqueryTable } from '../helpers/osquery_test_util';

initTestEnvironment();

/** Helper data structure to parse and expose all elements of interest from the OsqueryDetails DOM */
class OsqueryDetailsDOM {
  readonly inProgressDiv = this.rootElement.query(By.css('.in-progress'));
  readonly inProgressText = this.inProgressDiv?.nativeElement.innerText;

  readonly errorDiv = this.rootElement.query(By.css('.error'));
  readonly stdErrDiv = this.errorDiv?.query(By.css('div'));
  readonly stdErrText = this.stdErrDiv?.nativeElement.innerText;

  readonly displayedTableRoot? = this.rootElement.query(By.css('osquery-results-table'));
  readonly displayedTable = this.displayedTableRoot ? new OsqueryResultsTableDOM(this.displayedTableRoot) : null;

  readonly showAdditionalDiv = this.rootElement.query(By.css('.show-additional'));
  readonly showAdditionalButton = this.showAdditionalDiv?.query(By.css('button'));
  readonly showAdditionalButtonText = this.showAdditionalButton?.nativeElement.textContent;

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

    expect(parsedElements.displayedTable).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.showAdditionalDiv).toBeFalsy();

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
    expect(parsedElements.displayedTable).toBeFalsy();
    expect(parsedElements.showAdditionalDiv).toBeFalsy();

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

    expect(parsedElements.displayedTable).toBeTruthy();

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

    expect(parsedElements.displayedTable).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeTruthy();
    expect(parsedElements.showAdditionalButton).toBeTruthy();
    expect(parsedElements.showAdditionalButtonText).toBe('View all rows (1 more)');
  });

  it('should display the results table instead of the progress table when both present', () => {
    const resultColumns = ['resultCol1', 'resultCol2'];
    const resultCells = [['result-1-1', 'result-1-2'], ['result-2-1', 'result-2-2']];

    const progressColumns = ['progressCol1', 'progressCol2'];
    const progressCells = [['progress-1-1', 'progress-1-2']];

    const testFlowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        progress: {
          partialTable: newOsqueryTable('doesnt matter', progressColumns, progressCells),
          totalRowCount: 2,
        },
      }),
      resultSets: [
        newFlowResultSet({
          table: newOsqueryTable('doesnt matter', resultColumns, resultCells),
        }),
      ],
    };

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.displayedTable).toBeTruthy();
    expect(parsedElements.displayedTable?.columnsText).toEqual(resultColumns);
    expect(parsedElements.displayedTable?.cellsText).toEqual(resultCells.flat());
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
});
