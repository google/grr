import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiGetHuntClientCompletionStatsResult} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {FleetCollectionsStore} from '../../../store/fleet_collections_store';
import {
  newFleetCollectionsStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionProgressTable} from './fleet_collection_progress_table';
import {FleetCollectionProgressTableHarness} from './testing/fleet_collection_progress_table_harness';

initTestEnvironment();

async function createComponent(
  data: ApiGetHuntClientCompletionStatsResult | null | undefined,
  totalClients: bigint | null | undefined = BigInt(100),
) {
  const fixture = TestBed.createComponent(FleetCollectionProgressTable);
  fixture.componentRef.setInput('collectionProgressData', data);
  fixture.componentRef.setInput('totalClients', totalClients);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionProgressTableHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Progress Table Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FleetCollectionProgressTable, NoopAnimationsModule],
      providers: [
        {
          provide: FleetCollectionStore,
          useValue: newFleetCollectionStoreMock(),
        },
        {
          provide: FleetCollectionsStore,
          useValue: newFleetCollectionsStoreMock(),
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent({});

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows no rows and a message if table data is empty', async () => {
    const {harness} = await createComponent({
      startPoints: [],
      completePoints: [],
    });

    const table = await harness.table();
    expect(await harness.getRows()).toHaveSize(0);
    expect(await (await table.host()).text()).toContain(
      'There is no hunt progress data to show.',
    );
  });

  it('shows no rows and a message if table data undefined', async () => {
    const {harness} = await createComponent(undefined);

    const table = await harness.table();
    expect(await harness.getRows()).toHaveSize(0);
    expect(await (await table.host()).text()).toContain(
      'There is no hunt progress data to show.',
    );
  });

  it('shows all data in table', fakeAsync(async () => {
    const {harness} = await createComponent(
      {
        startPoints: [
          {
            xValue: 1669011100,
            yValue: 10,
          },
          {
            xValue: 1669022200,
            yValue: 20,
          },
        ],
        completePoints: [
          {
            xValue: 1669011100,
            yValue: 5,
          },
          {
            xValue: 1669022200,
            yValue: 10,
          },
        ],
      },
      BigInt(50),
    );

    const table = await harness.table();
    const header = await table.getHeaderRows();
    const headerCells = await header[0].getCells();
    expect(headerCells.length).toBe(3);
    expect(await headerCells[0].getText()).toBe('Date');
    expect(await headerCells[1].getText()).toBe('Completed clients');
    expect(await headerCells[2].getText()).toBe('Scheduled clients');

    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2022-11-21 06:11:40 UTC',
    );
    expect(await harness.getCellText(0, 'completedClients')).toBe('5 (10%)');
    expect(await harness.getCellText(0, 'scheduledClients')).toBe('10 (20%)');
    expect(await harness.getCellText(1, 'timestamp')).toContain(
      '2022-11-21 09:16:40 UTC',
    );
    expect(await harness.getCellText(1, 'completedClients')).toBe('10 (20%)');
    expect(await harness.getCellText(1, 'scheduledClients')).toBe('20 (40%)');
  }));
});
