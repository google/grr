import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {OsqueryResult as ApiOsqueryResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {OsqueryResults} from './osquery_results';
import {OsqueryResultsHarness} from './testing/osquery_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(OsqueryResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OsqueryResultsHarness,
  );

  return {fixture, harness};
}

describe('Osquery Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [OsqueryResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no tables if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.osqueryTables()).toHaveSize(0);
  }));

  it('shows a osquery result', fakeAsync(async () => {
    const osqueryResult: ApiOsqueryResult = {
      table: {
        query: 'SELECT * FROM test_table\nWHERE column = "FOO"',
        header: {columns: [{name: 'column'}]},
        rows: [{values: ['FOO']}],
      },
    };
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.OSQUERY_RESULT,
        payload: osqueryResult,
      }),
    ]);

    const tables = await harness.osqueryTables();
    expect(tables).toHaveSize(1);
    const table = tables[0];
    const rows = await table.getRows();
    expect(rows).toHaveSize(1);
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts).toEqual(['FOO']);
  }));

  it('shows a osquery result for hunt results', fakeAsync(async () => {
    const osqueryResult: ApiOsqueryResult = {
      table: {
        query: 'SELECT * FROM test_table\nWHERE column = "FOO"',
        header: {columns: [{name: 'column'}]},
        rows: [{values: ['FOO']}],
      },
    };
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.OSQUERY_RESULT,
        payload: osqueryResult,
      }),
    ]);

    const tables = await harness.osqueryTables();
    expect(tables).toHaveSize(1);
    const table = tables[0];
    const rows = await table.getRows();
    expect(rows).toHaveSize(1);
    const cells = await rows[0].getCells();
    const cellTexts = await Promise.all(cells.map((cell) => cell.getText()));
    expect(cellTexts[0]).toContain('C.1234');
    expect(cellTexts[1]).toContain('FOO');
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.OSQUERY_RESULT,
        payload: {
          table: {},
        },
      }),
      newFlowResult({
        payloadType: PayloadType.OSQUERY_RESULT,
        payload: {
          table: {},
        },
      }),
    ]);

    const table = await harness.osqueryTables();
    expect(table).toHaveSize(2);
  }));
});
