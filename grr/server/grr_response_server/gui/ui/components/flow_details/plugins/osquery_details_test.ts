import {DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {newOsqueryTable, OsqueryResultsTableDOM} from '@app/components/flow_details/helpers/osquery_test_util';
import {FlowListEntry, FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowListEntry, newFlowResultSet} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';
import {PluginsModule} from './module';

import {OsqueryDetails} from './osquery_details';


initTestEnvironment();

/**
 * Helper data structure to parse and expose all elements of interest from the
 * OsqueryDetails DOM
 */
class OsqueryDetailsDOM {
  readonly inProgressDiv? = this.rootElement.query(By.css('.in-progress'));
  readonly inProgressText? = this.inProgressDiv?.nativeElement.innerText;

  readonly errorDiv? = this.rootElement.query(By.css('.error'));
  readonly errorMessageDiv? = this.errorDiv?.query(By.css('div'));
  readonly errorMessageText? = this.errorMessageDiv?.nativeElement.innerText;

  readonly displayedTableRoot? =
      this.rootElement.query(By.css('osquery-results-table'));
  readonly displayedTable? = this.displayedTableRoot ?
                           new OsqueryResultsTableDOM(this.displayedTableRoot) :
                           null;

  readonly exportCsvButton? = this.findElementsWithSelectorAndText(
      '.export-button-holder a', 'Download results as CSV')[0];
  readonly exportCsvButtonText? = this.exportCsvButton?.nativeElement.innerText;
  readonly exportCsvButtonLink? =
      this.exportCsvButton?.nativeElement.attributes.href?.value;

  readonly downloadFilesButton? = this.findElementsWithSelectorAndText(
      '.export-button-holder a', 'Download collected files')[0];
  readonly downloadFilesButtonText? =
      this.downloadFilesButton?.nativeElement.innerText;
  readonly downloadFilesButtonLink? =
      this.downloadFilesButton?.nativeElement.attributes.href?.value;

  readonly showAdditionalDiv? =
      this.rootElement.query(By.css('.show-additional'));
  readonly showAdditionalButton? =
      this.showAdditionalDiv?.query(By.css('button'));
  readonly showAdditionalButtonText? =
      this.showAdditionalButton?.nativeElement.textContent;

  constructor(private readonly rootElement: DebugElement) {}

  private findElementsWithSelectorAndText(selector: string, text: string):
      DebugElement[] {
    return this.rootElement.queryAll(By.css(selector))
        .filter(element => element.nativeElement.textContent === text);
  }
}

/**
 * Function that creates a component fixture which is supplied with the
 * FlowListEntry value provided
 */
function createFixtureFrom(flowListEntry: FlowListEntry):
    ComponentFixture<OsqueryDetails> {
  const fixture = TestBed.createComponent(OsqueryDetails);
  fixture.componentInstance.flowListEntry = flowListEntry;
  fixture.detectChanges();

  return fixture;
}

describe('osquery-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],

          providers: [],
        })
        .compileComponents();
  }));

  it('should display only the query argument when flow is still running',
     () => {
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

  it('should display only the progress error message if the flow encounters an error',
     () => {
       const testFlowListEntry = newFlowListEntry({
         state: FlowState.ERROR,
         progress: {
           errorMessage: 'Some syntax error',
         },
         args: {
           query: 'Query that produces syntax errors',
         },
       });

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.inProgressDiv).toBeFalsy();
       expect(parsedElements.displayedTable).toBeFalsy();
       expect(parsedElements.showAdditionalDiv).toBeFalsy();

       expect(parsedElements.errorDiv).toBeTruthy();
       expect(parsedElements.errorMessageDiv).toBeTruthy();
       expect(parsedElements.errorMessageText).toEqual('Some syntax error');
     });

  it('should display progress table with no "show additional" section if results are not truncated',
     () => {
       const testQuery = 'grr?';
       const testColName = 'column';
       const testCellValue = 'grr!';

       const testFlowListEntry = newFlowListEntry({
         state: FlowState.FINISHED,
         progress: {
           partialTable:
               newOsqueryTable(testQuery, [testColName], [[testCellValue]]),
           totalRowCount: '1',  // Not more than the number of rows in the
                                // progress table (1),
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

  it('should display progress table, and a button with count to request more if results are truncated',
     () => {
       const testQuery = 'grr?';
       const testColName = 'column';
       const testCellValue = 'grr!';

       const testFlowListEntry = newFlowListEntry({
         state: FlowState.FINISHED,
         progress: {
           partialTable:
               newOsqueryTable(testQuery, [testColName], [[testCellValue]]),
           totalRowCount:
               '2',  // More than the number of rows in the progress table (1),
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
       expect(parsedElements.showAdditionalButtonText)
           .toBe('View all rows (1 more)');
     });

  it('should display the results table instead of the progress table when both present',
     () => {
       const resultColumns = ['resultCol1', 'resultCol2'];
       const resultCells =
           [['result-1-1', 'result-1-2'], ['result-2-1', 'result-2-2']];

       const progressColumns = ['progressCol1', 'progressCol2'];
       const progressCells = [['progress-1-1', 'progress-1-2']];

       const testFlowListEntry = {
         flow: newFlow({
           state: FlowState.FINISHED,
           progress: {
             partialTable: newOsqueryTable(
                 'doesnt matter', progressColumns, progressCells),
             totalRowCount: '2',
           },
         }),
         resultSets: [
           newFlowResultSet({
             table:
                 newOsqueryTable('doesnt matter', resultColumns, resultCells),
           }),
         ],
       };

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.displayedTable).toBeTruthy();
       expect(parsedElements.displayedTable?.columnsText)
           .toEqual(resultColumns);
       expect(parsedElements.displayedTable?.cellsText)
           .toEqual(resultCells.flat());
     });

  it('shouldn\'t display the show-additional section if flow is still in progress',
     () => {
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

  it('should display the show-additional section if no table or progress is available (for some reason)',
     () => {
       const testFlowListEntry = newFlowListEntry({
         state: FlowState.FINISHED,
       });

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.showAdditionalDiv).toBeTruthy();
       expect(parsedElements.showAdditionalButton).toBeTruthy();
       expect(parsedElements.showAdditionalButtonText)
           .toBe('View all rows (? more)');
     });

  it('doesn\'t display the show-additional section if totalRowCount in the progress is 0',
     () => {
       const testFlowListEntry = newFlowListEntry({
         state: FlowState.FINISHED,
         args: {
           query: 'Some query',
         },
         progress: {
           totalRowCount: '0',
         }
       });

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.showAdditionalDiv).toBeFalsy();
     });

  it('shouldn\'t display the export button if flow is still running', () => {
    const testFlowListEntry = newFlowListEntry({
      state: FlowState.RUNNING,
      args: {
        query: 'random',
      },
    });

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.exportCsvButton).toBeFalsy();
  });

  it('shouldn\'t display the export button if the flow encountered an error',
     () => {
       const testFlowListEntry = newFlowListEntry({
         state: FlowState.ERROR,
         args: {
           query: 'Some query',
         },
       });

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.exportCsvButton).toBeFalsy();
     });

  it('shouldn\'t display the export button if the table is empty', () => {
    const testFlowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        flowId: 'flowId',
        clientId: 'clientId',
      }),
      resultSets: [
        newFlowResultSet({
          table: newOsqueryTable('doesnt matter', ['c1', 'c2'], []),
        }),
      ],
    };

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

    expect(parsedElements.exportCsvButton).toBeFalsy();
  });

  it('should display the export button with correct href if the table is not empty',
     () => {
       const testFlowListEntry = {
         flow: newFlow({
           state: FlowState.FINISHED,
           clientId: 'someClient123',
           flowId: 'someFlow321',
         }),
         resultSets: [
           newFlowResultSet({
             table: newOsqueryTable('doesnt matter', ['column'], [['cell']]),
           }),
         ],
       };

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.exportCsvButton).toBeTruthy();
       expect(parsedElements.exportCsvButtonText)
           .toBe('Download results as CSV');
       expect(parsedElements.exportCsvButtonLink)
           .toBe(
               '/api/clients/someClient123/flows/someFlow321/osquery-results/CSV');
     });

  it('shouldn\'t display the download collected file button if no columns for collection are present',
     () => {
       const testFlowListEntry = {
         flow: newFlow({
           state: FlowState.FINISHED,
           clientId: 'someClient123',
           flowId: 'someFlow321',
         }),
         resultSets: [
           newFlowResultSet({
             table: newOsqueryTable('doesnt matter', ['column'], [['cell']]),
           }),
         ],
       };

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.downloadFilesButton).toBeFalsy();
     });

  it('should display the download collected file button if columns for collection are present',
     () => {
       const testFlowListEntry = {
         flow: newFlow({
           state: FlowState.FINISHED,
           clientId: 'someClient123',
           flowId: 'someFlow321',
           args: {
             // Columns for file collection are present
             fileCollectionColumns: ['column'],
           },
         }),
         resultSets: [
           newFlowResultSet({
             table: newOsqueryTable('doesnt matter', ['column'], [['cell']]),
           }),
         ],
       };

       const fixture = createFixtureFrom(testFlowListEntry);
       const parsedElements = new OsqueryDetailsDOM(fixture.debugElement);

       expect(parsedElements.downloadFilesButton).toBeTruthy();
       expect(parsedElements.downloadFilesButtonText)
           .toBe('Download collected files');
       expect(parsedElements.downloadFilesButtonLink)
           .toBe(
               '/api/clients/someClient123/flows/someFlow321/results/files-archive');
     });
});
