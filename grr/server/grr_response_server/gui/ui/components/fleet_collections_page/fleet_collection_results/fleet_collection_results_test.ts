import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newHuntResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {FleetCollectionResults} from './fleet_collection_results';
import {FleetCollectionResultsHarness} from './testing/fleet_collection_results_harness';

initTestEnvironment();

async function createComponent(fleetCollectionId = '1234') {
  const fixture = TestBed.createComponent(FleetCollectionResults);
  fixture.componentRef.setInput('fleetCollectionId', fleetCollectionId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionResultsHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Results Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionResults,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES),
      ],
      providers: [
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows correct number of results loaded', async () => {
    fleetCollectionStoreMock.fleetCollectionResults = signal([
      newHuntResult({}),
      newHuntResult({}),
    ]);
    fleetCollectionStoreMock.totalResultsCount = signal(3);

    const {harness} = await createComponent();

    expect(await harness.loadedResultsText()).toContain(
      '2 of 3 results loaded',
    );
  });

  it('shows `Load more` button if there are more results to load', async () => {
    fleetCollectionStoreMock.fleetCollectionResults = signal([
      newHuntResult({}),
      newHuntResult({}),
    ]);
    fleetCollectionStoreMock.totalResultsCount = signal(3);

    const {harness} = await createComponent();

    expect(await harness.hasLoadMoreButton()).toBeTrue();
  });

  it('does not show `Load more` button if there are no more results to load', async () => {
    fleetCollectionStoreMock.fleetCollectionResults = signal([
      newHuntResult({}),
      newHuntResult({}),
    ]);
    fleetCollectionStoreMock.totalResultsCount = signal(2);

    const {harness} = await createComponent();

    expect(await harness.hasLoadMoreButton()).toBeFalse();
  });

  it('shows results table with no rows when there are no results', async () => {
    fleetCollectionStoreMock.fleetCollectionResultsPerClientAndType = signal(
      [],
    );
    const {harness} = await createComponent();

    expect(await harness.getRows()).toHaveSize(0);
  });

  it('shows results table with correct columns', async () => {
    fleetCollectionStoreMock.fleetCollectionResultsPerClientAndType = signal([
      {
        clientId: 'C.1234',
        resultType: PayloadType.STAT_ENTRY,
        results: [newHuntResult({})],
      },
    ]);
    const {harness} = await createComponent();

    const table = await harness.resultsTable();
    const headerRows = await table.getHeaderRows();
    const headerRow = await headerRows[0].getCells();
    const headerRowText = await Promise.all(
      headerRow.map((cell) => cell.getText()),
    );
    expect(headerRowText).toEqual([
      '',
      'Client ID',
      'Result Type',
      'Result Count',
      'Details',
    ]);
    const rows = await harness.getRows();
    expect(rows.length).toBe(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
    expect(await harness.getCellText(0, 'resultType')).toContain('StatEntry');
    expect(await harness.getCellText(0, 'resultCount')).toBe('≥ 1');
    expect(await harness.getCellText(0, 'details')).toBe('keyboard_arrow_down');
  });

  it('initially collapses rows in results table', async () => {
    fleetCollectionStoreMock.fleetCollectionResultsPerClientAndType = signal([
      {
        clientId: 'C.1234',
        resultType: PayloadType.USER,
        results: [newHuntResult({})],
      },
    ]);
    const {harness} = await createComponent();

    expect(await harness.isDetailsExpanded(0)).toBeFalse();
    const clientResults = await harness.fleetCollectionClientResults();
    expect(clientResults).toHaveSize(0);
  });

  it('can expand rows of results table', async () => {
    fleetCollectionStoreMock.fleetCollectionResultsPerClientAndType = signal([
      {
        clientId: 'C.1234',
        resultType: PayloadType.USER,
        results: [newHuntResult({})],
      },
    ]);
    const {harness} = await createComponent();

    await harness.toggleDetails(0);

    expect(await harness.isDetailsExpanded(0)).toBeTrue();
    const clientResults = await harness.fleetCollectionClientResults();
    expect(clientResults).toHaveSize(1);
  });

  it('can expand multiple rows', async () => {
    fleetCollectionStoreMock.fleetCollectionResultsPerClientAndType = signal([
      {
        clientId: 'C.1234',
        resultType: PayloadType.USER,
        results: [newHuntResult({})],
      },
      {
        clientId: 'C.5678',
        resultType: PayloadType.STAT_ENTRY,
        results: [],
      },
    ]);

    const {harness} = await createComponent();

    await harness.toggleDetails(0);
    await harness.toggleDetails(1);

    expect(await harness.isDetailsExpanded(0)).toBeTrue();
    expect(await harness.isDetailsExpanded(1)).toBeTrue();
    const clientResults = await harness.fleetCollectionClientResults();
    expect(clientResults).toHaveSize(2);
  });

  it('shows download button', async () => {
    const {harness} = await createComponent();

    expect(await harness.downloadButton()).toBeDefined();
  });

  it('shows progress component', async () => {
    const {harness} = await createComponent();

    expect(await harness.progress()).toBeDefined();
  });
});
