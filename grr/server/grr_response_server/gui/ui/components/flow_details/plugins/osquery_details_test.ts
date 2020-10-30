import {async, TestBed, ComponentFixture} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';

import {PluginsModule} from './module';
import { OsqueryDetails } from './osquery_details';
import { FlowState } from '@app/lib/models/flow';
import { OsqueryFlowListEntryBuilder, ParsedOsqueryDetails } from '../helpers/osquery_test_utils';

initTestEnvironment();

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
   * Function that creates a component fixture which is supplied with the
   * FlowListEntry values provided by the builder
   */
  function createFixtureFrom(flowListEntryBuilder: OsqueryFlowListEntryBuilder)
    : ComponentFixture<OsqueryDetails> {
    const fixture = TestBed.createComponent(OsqueryDetails);
    fixture.componentInstance.flowListEntry = flowListEntryBuilder.build();
    fixture.detectChanges();

    return fixture;
  }

  it('should display only the query argument when flow is still running', () => {
    const testQuery = 'SELECT * FROM users LIMIT 10;';
    const testFlowListEntry = new OsqueryFlowListEntryBuilder()
      .withFlowState(FlowState.RUNNING)
      .withQuery(testQuery);
    const expectedQueryText = `Query in progress: ${testQuery}`;

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedOsqueryDetails(fixture.debugElement);

    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.progressTableDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();

    expect(parsedElements.inProgressDiv).toBeTruthy();
    expect(parsedElements.inProgressText).toEqual(expectedQueryText);
  });

  it('should display only the stderr error if the flow encounters an error', () => {
    const testStderr = 'just a standard err';
    const exptectedText = `stderr is: ${testStderr}`;
    const testFlowListEntry = new OsqueryFlowListEntryBuilder()
      .withFlowState(FlowState.ERROR)
      .withStderr(testStderr);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedOsqueryDetails(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();
    expect(parsedElements.progressTableDiv).toBeFalsy();

    expect(parsedElements.errorDiv).toBeTruthy();
    expect(parsedElements.stdErrDiv).toBeTruthy();
    expect(parsedElements.stdErrText).toEqual(exptectedText);
  });

  it('should display progress table with no "show additional" section if results are not truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = new OsqueryFlowListEntryBuilder()
      .withFlowState(FlowState.FINISHED)
      .withProgressTable([testColName], [[testCellValue]])
      .withProgressRowsCount(1) // Not more than the number of rows in the progress table(1)
      .withQuery(testQuery);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedOsqueryDetails(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();

    expect(parsedElements.progressTableDiv).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeFalsy();
  });

  it('should display progress table, correct label and a button to request more if results are truncated', () => {
    const testQuery = 'grr?';
    const testColName = 'column';
    const testCellValue = 'grr!';

    const testFlowListEntry = new OsqueryFlowListEntryBuilder()
      .withFlowState(FlowState.FINISHED)
      .withProgressTable([testColName], [[testCellValue]])
      .withProgressRowsCount(2) // More than the number of rows in the progress table (1)
      .withQuery(testQuery);

    const fixture = createFixtureFrom(testFlowListEntry);
    const parsedElements = new ParsedOsqueryDetails(fixture.debugElement);

    expect(parsedElements.inProgressDiv).toBeFalsy();
    expect(parsedElements.errorDiv).toBeFalsy();
    expect(parsedElements.resultsTableDiv).toBeFalsy();

    expect(parsedElements.progressTableDiv).toBeTruthy();

    expect(parsedElements.showAdditionalDiv).toBeTruthy();

    expect(parsedElements.showAdditionalTextDiv).toBeTruthy();
    expect(parsedElements.showAdditionalTextText).toEqual('1 row(s) hidden.');

    expect(parsedElements.showAdditionalButton).toBeTruthy();
  })
});
