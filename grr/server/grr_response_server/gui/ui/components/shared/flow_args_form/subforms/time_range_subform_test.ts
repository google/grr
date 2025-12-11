import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {TestBed, fakeAsync, tick, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {DateAdapter, MatNativeDateModule} from '@angular/material/core';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {TimeRangeSubformHarness} from './testing/time_range_subform_harness';
import {TimeRangeSubform, createTimeRangeFormGroup} from './time_range_subform';

initTestEnvironment();

@Component({
  selector: 'time-range-subform-test',
  template: `
    <form [formGroup]="formGroup">
      <time-range-subform [formGroup]="formGroup.controls.range"/>
    </form>
  `,
  imports: [CommonModule, TimeRangeSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    range: createTimeRangeFormGroup(),
  });
}

async function createComponent() {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    TimeRangeSubformHarness,
  );
  return {fixture, harness};
}
describe('Time Range Form component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TimeRangeSubform, MatNativeDateModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();

    // Set a fixed locale to avoid test location dependency.
    // This is likely going to fail when daylight savings time starts/ends.
    // TODO: This should be resolved when we switch to UTC time.
    TestBed.inject(DateAdapter).setLocale('en-US');
  }));

  it('displays form', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeDefined();
  });

  it('displays error message if neither field is filled', async () => {
    const {harness} = await createComponent();

    expect(await harness.hasFormErrors()).toBeTrue();
  });

  it('does not display error messages if one field is filled', async () => {
    const {harness} = await createComponent();
    await harness.setFromDate('01/01/2024');
    await harness.setFromTime('12:00');

    expect(await harness.hasFormErrors()).toBeFalse();
  });

  it('displays error message if min time is equal to max time', async () => {
    const {harness} = await createComponent();
    await harness.setFromDate('01/01/2024');
    await harness.setFromTime('12:00');

    await harness.setToDate('01/01/2024');
    await harness.setToTime('12:00');

    expect(await harness.hasFormErrors()).toBeTrue();
  });

  it('displays error message if min time is greater than max time', fakeAsync(async () => {
    const {harness} = await createComponent();
    await harness.setFromDate('01/01/2024 2:00 PM');

    await harness.setToDate('01/01/2023 1:00 PM');

    tick();
    expect(await harness.hasFormErrors()).toBeTrue();
  }));

  it('correctly exposes form values', async () => {
    const {harness, fixture} = await createComponent();

    await harness.setFromDate('01/01/2024 1:00');
    await harness.setToDate('01/02/2024 2:00');

    expect(fixture.componentInstance.formGroup.value.range).toEqual({
      fromTime: new Date(2024, 0, 1, 1, 0, 0),
      toTime: new Date(2024, 0, 2, 2, 0, 0),
    });
  });
});
