import {DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';

import {newOsqueryTable, OsqueryResultsTableDOM} from '../../../components/flow_details/helpers/osquery_test_util';
import {Flow, FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

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

  readonly showAdditionalDiv? =
      this.rootElement.query(By.css('.show-additional'));
  readonly showAdditionalButton? =
      this.showAdditionalDiv?.query(By.css('button'));
  readonly showAdditionalButtonText? =
      this.showAdditionalButton?.nativeElement.textContent;

  constructor(private readonly rootElement: DebugElement) {}
}

/**
 * Function that creates a component fixture which is supplied with the Flow
 * value provided.
 */
function createFixtureFrom(flow: Flow): ComponentFixture<OsqueryDetails> {
  const fixture = TestBed.createComponent(OsqueryDetails);
  fixture.componentInstance.flow = flow;
  fixture.detectChanges();

  return fixture;
}

describe('osquery-details component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('should display only the query argument when flow is still running',
     () => {
       const testQuery = 'SELECT * FROM users LIMIT 10;';
       const testFlowListEntry = newFlow({
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
       const testFlowListEntry = newFlow({
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

       const testFlowListEntry = newFlow({
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

       const testFlowListEntry = newFlow({
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

       const testFlowListEntry = newFlow({
         state: FlowState.FINISHED,
         progress: {
           partialTable:
               newOsqueryTable('doesnt matter', progressColumns, progressCells),
           totalRowCount: '2',
         },
       });

       const fixture = createFixtureFrom(testFlowListEntry);

       flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
         payload: {
           table: newOsqueryTable('doesnt matter', resultColumns, resultCells),
         }
       })]);
       fixture.detectChanges();

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
       const testFlowListEntry = newFlow({
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
       const testFlowListEntry = newFlow({
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
       const testFlowListEntry = newFlow({
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

  it('shouldn\'t display the download collected file button if no columns for collection are present',
     () => {
       const testFlowListEntry = newFlow({
         state: FlowState.FINISHED,
         clientId: 'someClient123',
         flowId: 'someFlow321',
       });

       const fixture = createFixtureFrom(testFlowListEntry);

       flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
         payload: {
           table: newOsqueryTable('doesnt matter', ['column'], [['cell']]),
         }
       })]);

       expect(fixture.componentInstance.getExportMenuItems(
                  fixture.componentInstance.flow)[0])
           .not.toEqual(
               fixture.componentInstance.getDownloadFilesExportMenuItem(
                   fixture.componentInstance.flow));
     });

  it('should display the download collected file button if columns for collection are present',
     () => {
       const testFlowListEntry = newFlow({
         state: FlowState.FINISHED,
         clientId: 'someClient123',
         flowId: 'someFlow321',
         args: {
           // Columns for file collection are present
           fileCollectionColumns: ['column'],
         },
         progress: {
           totalRowCount: 1,
         }
       });

       const fixture = createFixtureFrom(testFlowListEntry);

       flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
         payload: {
           table: newOsqueryTable('doesnt matter', ['column'], [['cell']]),
         }
       })]);
       fixture.detectChanges();

       expect(fixture.componentInstance.getExportMenuItems(
                  fixture.componentInstance.flow)[0])
           .toEqual(fixture.componentInstance.getDownloadFilesExportMenuItem(
               fixture.componentInstance.flow));
     });
});
