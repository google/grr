import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';
import {TimestampHarness} from './testing/timestamp_harness';
import {RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS, Timestamp} from './timestamp';

initTestEnvironment();

async function createComponent(
  date?: Date,
  relativeTimestamp?: 'visible' | 'hidden' | 'tooltip',
) {
  const fixture = TestBed.createComponent(Timestamp);
  if (date) {
    fixture.componentRef.setInput('date', date);
  }
  if (relativeTimestamp) {
    fixture.componentRef.setInput('relativeTimestamp', relativeTimestamp);
  }
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    TimestampHarness,
  );
  return {fixture, harness};
}

describe('Timestamp Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [Timestamp, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created successfully', fakeAsync(async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  }));

  it('is blank when no date is provided', fakeAsync(async () => {
    const {harness} = await createComponent();
    expect(await harness.hasTimestamp()).toBeFalse();
  }));

  it('shows absolute timestamp in tooltip by default', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T12:59:59+00:00'),
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);

    expect(await harness.getTimestampText()).toContain(
      '2020-07-01 12:59:59 UTC',
    );
    expect(
      await harness.showsRelativeTimestamp('less than 1 minute ago'),
    ).toBeFalse();
    const timestamp = await harness.getCopyButton();
    expect(await timestamp.getTooltipText()).toEqual('less than 1 minute ago');
  }));

  it('shows no relative timestamp or tooltip when relativeTimestamp is set to hidden', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T12:00:00.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'hidden',
    );
    tick();
    expect(await harness.showsRelativeTimestamp('1 hour ago')).toBeFalse();
    expect(
      await (await harness.getCopyButton()).isTooltipDisabled(),
    ).toBeTrue();
  }));

  it('shows the relative timestamp when relativeTimestamp is set to visible', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));
    const {harness, fixture} = await createComponent(
      new Date('2020-07-01T12:50:00+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    fixture.detectChanges();
    expect(await harness.getTimestampText()).toContain(
      '2020-07-01 12:50:00 UTC',
    );
    expect(await harness.showsRelativeTimestamp('10 minutes ago')).toBeTrue();
  }));

  it('shows only tooltip when relativeTimestamp is set to tooltip', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));

    const {harness} = await createComponent(
      new Date('2020-07-01T12:50:00+00:00'),
      'tooltip',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('10 minutes ago')).toBeFalse();
    const timestamp = await harness.getCopyButton();
    expect(await timestamp.isTooltipDisabled()).toBeFalse();
    expect(await timestamp.getTooltipText()).toEqual('10 minutes ago');
  }));

  it('renders "less than 1 minute ago" for a diff of 50 seconds', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:50.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(
      await harness.showsRelativeTimestamp('less than 1 minute ago'),
    ).toBeTrue();
  }));

  it('renders "less than 1 minute ago" for a diff of 1s', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(
      await harness.showsRelativeTimestamp('less than 1 minute ago'),
    ).toBeTrue();
  }));

  it('renders 1 minute ago for a diff of 60 seconds', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:01:00.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('1 minute ago')).toBeTrue();
  }));

  it('renders 59 minutes ago for a diff of 59 minutes', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:59:00.000+00:00'));

    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS); // 59 minutes
    expect(await harness.showsRelativeTimestamp('59 minutes ago')).toBeTrue();
  }));

  it('renders 1 hour ago for a diff of 60 minutes', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T14:00:00.000+00:00'));
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('1 hour ago')).toBeTrue();
  }));

  it('changes value when input date is changed', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));

    const {fixture, harness} = await createComponent(
      new Date('2020-07-01T12:00:00.000+00:00'),
      'visible',
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('1 hour ago')).toBeTrue();

    fixture.componentRef.setInput(
      'date',
      new Date('2020-07-01T11:00:00.000+00:00'),
    );
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('2 hours ago')).toBeTrue();
  }));

  it('changes relative timestamp when time passes', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Date('2020-07-01T13:00:00.000+00:00'),
      'visible',
    );

    jasmine.clock().mockDate(new Date('2020-07-01T13:01:00.000+00:00'));
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('1 minute ago')).toBeTrue();

    jasmine.clock().mockDate(new Date('2020-07-01T13:02:00.000+00:00'));
    tick(RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
    expect(await harness.showsRelativeTimestamp('2 minutes ago')).toBeTrue();
  }));
});
