import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newHunt} from '../../../lib/models/model_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionProgress} from './fleet_collection_progress';
import {FleetCollectionProgressHarness} from './testing/fleet_collection_progress_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionProgress);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionProgressHarness,
  );

  return {fixture, harness};
}
describe('Fleet Collection Progress Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();
    TestBed.configureTestingModule({
      imports: [FleetCollectionProgress, NoopAnimationsModule],
      providers: [
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('displays stats for fleet collection', async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        allClientsCount: BigInt(100),
        completedClientsCount: BigInt(3),
        remainingClientsCount: BigInt(25),
        clientsWithResultsCount: BigInt(1),
        crashedClientsCount: BigInt(2),
        failedClientsCount: BigInt(3),
      }),
    );
    const {harness} = await createComponent();

    const summaries = await harness.getCollectionSummaries();

    expect(summaries.length).toBe(7);
    expect(summaries[0]).toContain('Total');
    expect(summaries[0]).toContain('100 clients');

    expect(summaries[1]).toContain('Complete');
    expect(summaries[1]).toContain('3 %');
    expect(summaries[1]).toContain('3 clients');

    expect(summaries[2]).toContain('In progress');
    expect(summaries[2]).toContain('25 %');
    expect(summaries[2]).toContain('25 clients');

    expect(summaries[3]).toContain('Without results');
    expect(summaries[3]).toContain('2 %');
    expect(summaries[3]).toContain('2 clients');

    expect(summaries[4]).toContain('With results');
    expect(summaries[4]).toContain('1 %');
    expect(summaries[4]).toContain('1 client');

    expect(summaries[5]).toContain('Errors');
    expect(summaries[5]).toContain('3 %');
    expect(summaries[5]).toContain('3 clients');

    expect(summaries[6]).toContain('Crashes');
    expect(summaries[6]).toContain('2 %');
    expect(summaries[6]).toContain('2 clients');
  });

  it('initially displays progress chart and hides table', async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        allClientsCount: BigInt(100),
      }),
    );

    const {harness} = await createComponent();

    expect(await harness.progressChart()).toBeDefined();
    expect(await harness.progressTable()).toBeNull();
  });

  it('shows the progress chart and table when there is progress data', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        allClientsCount: BigInt(0),
      }),
    );
    fleetCollectionStoreMock.fleetCollectionProgress = signal({
      startPoints: [
        {
          xValue: 1678379900,
          yValue: 10,
        },
      ],
      completePoints: [
        {
          xValue: 1678379900,
          yValue: 5,
        },
      ],
    });

    const {harness} = await createComponent();

    const collapsibleTitles = await harness.collapsibleTitles();
    expect(collapsibleTitles.length).toBe(2);
    expect(await collapsibleTitles[0].text()).toContain(
      'Collection Progress Chart',
    );
    expect(await collapsibleTitles[1].text()).toContain(
      'Collection Progress Table',
    );
  }));

  it('does not show the progress sections when there is no progress data', async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        allClientsCount: BigInt(0),
      }),
    );
    fleetCollectionStoreMock.fleetCollectionProgress = signal(null);
    const {harness} = await createComponent();

    const collapsibleTitles = await harness.collapsibleTitles();
    expect(collapsibleTitles.length).toBe(0);
  });

  it('shows message when there is no progress data', async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        allClientsCount: BigInt(0),
      }),
    );
    fleetCollectionStoreMock.fleetCollectionProgress = signal(null);
    const {harness} = await createComponent();

    expect(await harness.getNoProgressData()).toBe(
      'There is no fleet collection progress data to show.',
    );
  });
});
