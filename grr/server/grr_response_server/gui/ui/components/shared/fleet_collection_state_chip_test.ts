import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiHuntStateReason} from '../../lib/api/api_interfaces';
import {HuntState} from '../../lib/models/hunt';
import {initTestEnvironment} from '../../testing';
import {FleetCollectionStateChip} from './fleet_collection_state_chip';
import {FleetCollectionStateChipHarness} from './testing/fleet_collection_state_chip_harness';

initTestEnvironment();

async function createComponent(
  fleetCollectionState: HuntState,
  resultsCount?: bigint,
  fleetCollectionStateReason: ApiHuntStateReason = ApiHuntStateReason.UNKNOWN,
  fleetCollectionStateComment?: string,
) {
  const fixture = TestBed.createComponent(FleetCollectionStateChip);
  fixture.componentRef.setInput('fleetCollectionState', fleetCollectionState);
  fixture.componentRef.setInput(
    'fleetCollectionStateReason',
    fleetCollectionStateReason,
  );
  fixture.componentRef.setInput(
    'fleetCollectionStateComment',
    fleetCollectionStateComment,
  );
  fixture.componentRef.setInput('resultsCount', resultsCount);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionStateChipHarness,
  );
  return {fixture, harness};
}

describe('Fleet Collection State Icon Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FleetCollectionStateChip, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created successfully', async () => {
    const {fixture} = await createComponent(HuntState.NOT_STARTED);

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows the correct number in the badge', async () => {
    const {harness} = await createComponent(HuntState.RUNNING, BigInt(10));

    const badge = await harness.badge();
    expect(await badge!.getText()).toBe('10');
  });

  it('does not show the badge if the collection has not started', async () => {
    const {harness} = await createComponent(HuntState.NOT_STARTED, BigInt(0));

    const badge = await harness.badge();
    expect(badge).toBeNull();
  });

  it('shows the correct icon and chip for NOT_STARTED state', async () => {
    const {harness} = await createComponent(HuntState.NOT_STARTED);

    const icon = await harness.icon();
    expect(await icon.getName()).toBe('not_started');
    expect(await harness.getChipText()).toContain('Not started');
  });

  it('shows the correct tooltip for NOT_STARTED state', async () => {
    const {harness} = await createComponent(HuntState.NOT_STARTED);

    expect(await harness.getTooltipText()).toBe('Fleet collection not started');
  });

  it('shows the correct icon and chip for RUNNING state', async () => {
    const {harness} = await createComponent(HuntState.RUNNING);

    const icon = await harness.icon();
    expect(await icon.getName()).toBe('hourglass_top');
    expect(await harness.getChipText()).toContain('Running');
  });

  it('shows the correct tooltip for RUNNING state', async () => {
    const {harness} = await createComponent(HuntState.RUNNING, BigInt(10));

    expect(await harness.getTooltipText()).toBe(
      'Fleet collection running; 10 clients returned results',
    );
  });

  it('shows the correct icon and chip for REACHED_CLIENT_LIMIT state', async () => {
    const {harness} = await createComponent(HuntState.REACHED_CLIENT_LIMIT);

    const icon = await harness.icon();
    expect(await icon.getName()).toBe('pause_circle');
    expect(await harness.getChipText()).toContain(
      'Paused - reached client limit',
    );
  });

  it('shows the correct tooltip for REACHED_CLIENT_LIMIT state', async () => {
    const {harness} = await createComponent(
      HuntState.REACHED_CLIENT_LIMIT,
      BigInt(10),
    );

    expect(await harness.getTooltipText()).toBe(
      'Fleet collection paused - reached client limit; 10 clients returned results',
    );
  });

  it('shows the correct icon and chip for REACHED_TIME_LIMIT state', async () => {
    const {harness} = await createComponent(HuntState.REACHED_TIME_LIMIT);

    const icon = await harness.icon();
    expect(await icon.getName()).toBe('check_circle');
    expect(await harness.getChipText()).toContain(
      'Completed - reached time limit',
    );
  });

  it('shows the correct tooltip for REACHED_TIME_LIMIT state', async () => {
    const {harness} = await createComponent(
      HuntState.REACHED_TIME_LIMIT,
      BigInt(10),
    );

    expect(await harness.getTooltipText()).toBe(
      'Fleet collection completed - reached time limit; 10 clients returned results',
    );
  });

  it('shows the correct icon and chip for CANCELLED state', async () => {
    const {harness} = await createComponent(HuntState.CANCELLED);

    const icon = await harness.icon();
    expect(await icon.getName()).toBe('cancel');
    expect(await harness.getChipText()).toContain('Cancelled');
  });

  it('shows the correct tooltip for CANCELLED state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      BigInt(10),
      ApiHuntStateReason.DEADLINE_REACHED,
      'test comment',
    );

    expect(await harness.getTooltipText()).toBe(
      'Fleet collection cancelled - test comment; 10 clients returned results',
    );
  });

  it('shows the cancellation reason for unknown state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.UNKNOWN,
    );

    expect(await harness.getChipText()).toContain('Unknown reason');
  });

  it('shows the cancellation reason for deadline exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.DEADLINE_REACHED,
    );

    expect(await harness.getChipText()).toContain('Deadline exceeded');
  });

  it('shows the cancellation reason for total clients exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.TOTAL_CLIENTS_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain('Too many clients');
  });

  it('shows the cancellation reason for total crashes exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.TOTAL_CRASHES_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain('Too many client crashes');
  });

  it('shows the cancellation reason for total network exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.TOTAL_NETWORK_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain(
      'Too much network used across fleet',
    );
  });

  it('shows the cancellation reason for avg results exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.AVG_RESULTS_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain(
      'Too many results per client',
    );
  });

  it('shows the cancellation reason for avg network exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.AVG_NETWORK_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain(
      'Too much network used per client',
    );
  });

  it('shows the cancellation reason for avg cpu exceeded state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.AVG_CPU_EXCEEDED,
    );

    expect(await harness.getChipText()).toContain(
      'Too much CPU used per client',
    );
  });

  it('shows the cancellation reason for triggered by user state', async () => {
    const {harness} = await createComponent(
      HuntState.CANCELLED,
      undefined,
      ApiHuntStateReason.TRIGGERED_BY_USER,
    );

    expect(await harness.getChipText()).toContain('Cancelled by user');
  });
});
