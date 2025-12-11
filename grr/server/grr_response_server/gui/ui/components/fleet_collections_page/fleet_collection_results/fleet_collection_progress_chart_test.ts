import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {ApiGetHuntClientCompletionStatsResult} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionProgressChart} from './fleet_collection_progress_chart';
import {FleetCollectionProgressChartHarness} from './testing/fleet_collection_progress_chart_harness';

initTestEnvironment();

async function createComponent(
  data: ApiGetHuntClientCompletionStatsResult | null | undefined,
) {
  const fixture = TestBed.createComponent(FleetCollectionProgressChart);
  fixture.componentRef.setInput('collectionProgressData', data);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionProgressChartHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Progress Chart Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FleetCollectionProgressChart],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent({});

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows a message if fleet collection completion progress data is null', async () => {
    const {harness} = await createComponent(undefined);

    const noDataBlock = await harness.noDataBlock();
    expect(noDataBlock).not.toBeNull();
    expect(await noDataBlock!.text()).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a message if hunt completion progress data is empty', async () => {
    const {harness} = await createComponent({
      completePoints: [],
      startPoints: [],
    });

    const noDataBlock = await harness.noDataBlock();
    expect(noDataBlock).not.toBeNull();
    expect(await noDataBlock!.text()).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a message if hunt completion progress data has only 1 data-point', async () => {
    const {harness} = await createComponent({
      completePoints: [{xValue: 1669026900000, yValue: 0}],
      startPoints: [{xValue: 1669026900000, yValue: 0}],
    });

    const noDataBlock = await harness.noDataBlock();
    expect(noDataBlock).not.toBeNull();
    expect(await noDataBlock!.text()).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a svg element if hunt completion progress data is valid', async () => {
    const {harness} = await createComponent({
      completePoints: [
        {xValue: 1669011100, yValue: 0},
        {xValue: 1669022200, yValue: 0},
        {xValue: 1669033300, yValue: 0},
      ],
      startPoints: [
        {xValue: 1669011100, yValue: 0},
        {xValue: 1669022200, yValue: 7},
        {xValue: 1669033300, yValue: 29},
      ],
    });

    const svg = await harness.svg();
    expect(svg).not.toBeNull();
  });
});
