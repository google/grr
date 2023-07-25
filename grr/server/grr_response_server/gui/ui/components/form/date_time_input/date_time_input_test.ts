import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {MatCalendarHarness} from '@angular/material/datepicker/testing';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatMenuItemHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {DateTime} from '../../../lib/date_time';
import {initTestEnvironment} from '../../../testing';

import {DATE_TIME_FORMAT} from './date_time_input';
import {DateTimeInputModule} from './module';



initTestEnvironment();

@Component({
  template: `
  <mat-form-field appearance="outline">
    <date-time-input #dateTimeInput [formControl]="formControl"></date-time-input>
    <date-time-input-toggle [for]="dateTimeInput" matSuffix></date-time-input-toggle>
  </mat-form-field>
`
})
class TestHostComponent {
  readonly formControl = new UntypedFormControl();
}

describe('DateTimeInput Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ReactiveFormsModule,
            MatFormFieldModule,
            DateTimeInputModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function createComponent(): ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    return fixture;
  }

  it('reports null by default', () => {
    const fixture = createComponent();
    expect(fixture.componentInstance.formControl.value).toBeNull();
  });

  it('reports an error for an invalid date/time input', () => {
    const fixture = createComponent();

    const input = fixture.debugElement.query(By.css('input'));
    input.nativeElement.value = 'invalid';
    input.triggerEventHandler('input', {target: input.nativeElement});
    input.triggerEventHandler('change', {target: input.nativeElement});
    fixture.detectChanges();

    expect(fixture.componentInstance.formControl.errors).toEqual({
      invalidDateTime:
          `The input "invalid" can't be parsed as format ${DATE_TIME_FORMAT}`
    });
  });

  it('reports a DateTime object for a valid date/time input', () => {
    const fixture = createComponent();

    const input = fixture.debugElement.query(By.css('input'));
    input.nativeElement.value = '2021-01-02 03:04:05';
    input.triggerEventHandler('input', {target: input.nativeElement});
    input.triggerEventHandler('change', {target: input.nativeElement});
    fixture.detectChanges();

    expect(fixture.componentInstance.formControl.errors).toEqual(null);

    const value: DateTime = fixture.componentInstance.formControl.value;
    const expectedValue =
        DateTime.fromISO('2021-01-02T03:04:05.000Z', {zone: 'UTC'});
    expect(value.equals(expectedValue)).toBeTrue();
  });

  it('updates the input when form control value is set', async () => {
    const fixture = createComponent();
    const loader = TestbedHarnessEnvironment.loader(fixture);

    fixture.componentInstance.formControl.setValue(
        DateTime.fromISO('2020-07-01T03:04:05.000Z', {zone: 'UTC'}));
    fixture.detectChanges();

    const input = await loader.getHarness<MatInputHarness>(MatInputHarness);
    expect(await input.getValue()).toBe('2020-07-01 03:04:05');
  });

  it('inserts selected date with calendar icon click in empty input',
     fakeAsync(async () => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000Z'));

       const fixture = createComponent();
       const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);

       const calendarButton =
           fixture.debugElement.query(By.css('.calendar-toggle'));
       calendarButton.nativeElement.click();
       fixture.detectChanges();

       const calendar =
           await loader.getHarness<MatCalendarHarness>(MatCalendarHarness);
       const cells = await calendar.getCells();
       await calendar.selectCell({text: await cells[0].getText()});
       fixture.detectChanges();

       const result: DateTime = fixture.componentInstance.formControl.value;
       expect(result.toISO()).toEqual('2020-07-01T00:00:00.000Z');
     }));

  it('inserts selected time with current date on clocks click in empty input',
     fakeAsync(async () => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000Z'));

       const fixture = createComponent();
       const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);

       const clockMenuButton =
           fixture.debugElement.query(By.css('.clock-toggle'));
       clockMenuButton.nativeElement.click();
       fixture.detectChanges();

       const menuItem = await loader.getHarness<MatMenuItemHarness>(
           MatMenuItemHarness.with({text: '12:45'}));
       await menuItem.click();
       fixture.detectChanges();

       const result: DateTime = fixture.componentInstance.formControl.value;
       expect(result.toISO()).toEqual('2020-07-01T12:45:00.000Z');
     }));

  it('updates existing input with date on calendar icon click',
     fakeAsync(async () => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000Z'));

       const fixture = createComponent();
       const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);

       const input = fixture.debugElement.query(By.css('input'));
       input.nativeElement.value = '2021-01-02 03:04:05';
       input.triggerEventHandler('input', {target: input.nativeElement});
       input.triggerEventHandler('change', {target: input.nativeElement});
       fixture.detectChanges();

       const calendarButton =
           fixture.debugElement.query(By.css('.calendar-toggle'));
       calendarButton.nativeElement.click();
       fixture.detectChanges();

       const calendar =
           await loader.getHarness<MatCalendarHarness>(MatCalendarHarness);
       const cells = await calendar.getCells();
       await calendar.selectCell({text: await cells[0].getText()});
       fixture.detectChanges();

       const result: DateTime = fixture.componentInstance.formControl.value;
       expect(result.toISO()).toEqual('2020-07-01T03:04:05.000Z');
     }));

  it('updates existing input with time on clocks icon click',
     fakeAsync(async () => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000Z'));

       const fixture = createComponent();
       const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);

       const input = fixture.debugElement.query(By.css('input'));
       input.nativeElement.value = '2021-01-02 03:04:05';
       input.triggerEventHandler('input', {target: input.nativeElement});
       input.triggerEventHandler('change', {target: input.nativeElement});
       fixture.detectChanges();

       const clockMenuButton =
           fixture.debugElement.query(By.css('.clock-toggle'));
       clockMenuButton.nativeElement.click();
       fixture.detectChanges();

       const menuItem = await loader.getHarness<MatMenuItemHarness>(
           MatMenuItemHarness.with({text: '12:45'}));
       await menuItem.click();
       fixture.detectChanges();

       const result: DateTime = fixture.componentInstance.formControl.value;
       expect(result.toISO()).toEqual('2021-01-02T12:45:00.000Z');
     }));
});
