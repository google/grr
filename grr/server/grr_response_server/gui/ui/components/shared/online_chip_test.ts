import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {
  discardPeriodicTasks,
  fakeAsync,
  TestBed,
  tick,
  waitForAsync,
} from '@angular/core/testing';

import {initTestEnvironment} from '../../testing';
import {OnlineChip} from './online_chip';
import {OnlineChipHarness} from './testing/online_chip_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(OnlineChip);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OnlineChipHarness,
  );
  return {fixture, harness};
}

describe('Online Chip Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [OnlineChip],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created successfully', fakeAsync(async () => {
    const {fixture} = await createComponent();
    tick();
    expect(fixture.componentInstance).toBeTruthy();
    discardPeriodicTasks();
  }));

  it('shows "Offline" if lastSeen is undefined', fakeAsync(async () => {
    const {harness, fixture} = await createComponent();

    fixture.componentRef.setInput('lastSeen', undefined);
    tick();
    expect(await harness.hasOfflineChip()).toBeTrue();
  }));

  it('shows "Online" for clients last seen up to 15 minutes ago', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000'));

    const {harness, fixture} = await createComponent();

    fixture.componentRef.setInput('lastSeen', new Date('2020-07-01T12:50:00'));
    tick();
    expect(await harness.hasOnlineChip()).toBeTrue();

    discardPeriodicTasks();
  }));

  it('shows "Offline" for clients last seen more than 15 minutes ago', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000'));

    const {harness, fixture} = await createComponent();

    fixture.componentRef.setInput(
      'lastSeen',
      new Date('2020-07-01T12:40:00.000'),
    );
    tick();
    expect(await harness.hasOfflineChip()).toBeTrue();

    discardPeriodicTasks();
  }));

  it('updates the status to "Offline" for clients last seen more than 15 minutes ago', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000'));

    const {harness, fixture} = await createComponent();

    fixture.componentRef.setInput(
      'lastSeen',
      new Date('2020-07-01T13:00:00.000'),
    );
    tick();
    expect(await harness.hasOnlineChip()).toBeTrue();

    jasmine.clock().mockDate(new Date('2020-07-01T13:15:00.000'));
    // We update the status every 10 seconds.
    tick(10000);
    expect(await harness.hasOfflineChip()).toBeTrue();
  }));

  it('updates the status to "Online" when lastSeen updates', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000'));

    const {harness, fixture} = await createComponent();

    fixture.componentRef.setInput(
      'lastSeen',
      new Date('2020-07-01T12:00:00.000'),
    );
    tick();
    expect(await harness.hasOfflineChip()).toBeTrue();

    fixture.componentRef.setInput(
      'lastSeen',
      new Date('2020-07-01T13:00:00.000'),
    );
    tick();
    expect(await harness.hasOnlineChip()).toBeTrue();

    discardPeriodicTasks();
  }));
});
