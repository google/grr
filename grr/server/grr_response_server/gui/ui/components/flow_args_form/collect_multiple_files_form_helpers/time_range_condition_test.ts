import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {createTimeRangeFormGroup, formValuesToFileFinderAccessTimeCondition, formValuesToFileFinderInodeChangeTimeCondition, formValuesToFileFinderModificationTimeCondition, RawFormValues} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/time_range_condition';
import {DateTimeInputHarness} from '@app/components/form/date_time_input/testing/date_time_input_harness';
import {FileFinderAccessTimeCondition, FileFinderInodeChangeTimeCondition, FileFinderModificationTimeCondition} from '@app/lib/api/api_interfaces';
import {DateTime} from '@app/lib/date_time';
import {dateTimeEqualityTester, initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';
import {HelpersModule} from './module';




initTestEnvironment();

// NOTE: without a TestHostComponent with a form element, Angular has issues
// injecting ControlContainer into the date-time-input.
@Component({
  template: `
<div [formGroup]="form">
  <time-range-condition
    formGroupName="condition"
    (conditionRemoved)="conditionRemoved$.next()">
  </time-range-condition>
</div>
`
})
class TestHostComponent {
  readonly form = new FormGroup({
    condition: createTimeRangeFormGroup(),
  });

  readonly conditionRemoved$ = new Subject<void>();
}


describe('TimeRangeCondition component', () => {
  beforeEach(waitForAsync(() => {
    jasmine.addCustomEqualityTester(dateTimeEqualityTester);

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FormsModule,
            ReactiveFormsModule,
            MatFormFieldModule,
            HelpersModule,
          ],
          declarations: [TestHostComponent],

          providers: []
        })
        .compileComponents();
  }));

  function createComponent(): ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    return fixture;
  }

  it('displays error message if neither field is filled', () => {
    const fixture = createComponent();

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error.nativeElement.textContent)
        .toContain('Either one or both times have to be set');
  });

  it('does not display error messages if one field is filled', async () => {
    const fixture = createComponent();
    const loader = TestbedHarnessEnvironment.loader(fixture);

    const time = DateTime.fromSeconds(4242);
    const input = await loader.getHarness<DateTimeInputHarness>(
        DateTimeInputHarness.with({selector: '[formControlName="minTime"]'}));
    await input.setValue(time);

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeNull();
  });

  it('displays error message if min time is equal to max time', async () => {
    const fixture = createComponent();
    const loader = TestbedHarnessEnvironment.loader(fixture);

    const time = DateTime.fromSeconds(4242);
    const minInput = await loader.getHarness<DateTimeInputHarness>(
        DateTimeInputHarness.with({selector: '[formControlName="minTime"]'}));
    await minInput.setValue(time);

    const maxInput = await loader.getHarness<DateTimeInputHarness>(
        DateTimeInputHarness.with({selector: '[formControlName="maxTime"]'}));
    await maxInput.setValue(time);

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error.nativeElement.textContent)
        .toContain('Min timestamp has to be strictly before the max timestamp');
  });

  it('displays error message if min time is greater than max time',
     async () => {
       const fixture = createComponent();
       const loader = TestbedHarnessEnvironment.loader(fixture);

       const time1 = DateTime.fromSeconds(4242);
       const time2 = DateTime.fromSeconds(4241);
       const minInput = await loader.getHarness<DateTimeInputHarness>(
           DateTimeInputHarness.with(
               {selector: '[formControlName="minTime"]'}));
       await minInput.setValue(time1);

       const maxInput = await loader.getHarness<DateTimeInputHarness>(
           DateTimeInputHarness.with(
               {selector: '[formControlName="maxTime"]'}));
       await maxInput.setValue(time2);

       const error = fixture.debugElement.query(By.css('mat-error'));
       expect(error.nativeElement.textContent)
           .toContain(
               'Min timestamp has to be strictly before the max timestamp');
     });

  it('correctly exposes form value', async () => {
    const fixture = createComponent();
    const loader = TestbedHarnessEnvironment.loader(fixture);

    const minTime = DateTime.fromSeconds(4242);
    const minInput = await loader.getHarness<DateTimeInputHarness>(
        DateTimeInputHarness.with({selector: '[formControlName="minTime"]'}));
    await minInput.setValue(minTime);

    const maxTime = DateTime.fromSeconds(4243);
    const maxInput = await loader.getHarness<DateTimeInputHarness>(
        DateTimeInputHarness.with({selector: '[formControlName="maxTime"]'}));
    await maxInput.setValue(maxTime);

    const expected: RawFormValues = {
      minTime,
      maxTime,
    };
    expect(fixture.componentInstance.form.value.condition).toEqual(expected);
  });
});

describe('formValuesToFileFinderModificationTimeCondition()', () => {
  it('correctly converts empty form value', () => {
    const source: RawFormValues = {
      minTime: null,
      maxTime: null,
    };
    const expected: FileFinderModificationTimeCondition = {
      minLastModifiedTime: undefined,
      maxLastModifiedTime: undefined,
    };
    expect(formValuesToFileFinderModificationTimeCondition(source))
        .toEqual(expected);
  });

  it('correctly converts filled out form value', () => {
    const source: RawFormValues = {
      minTime: DateTime.fromSeconds(4242),
      maxTime: DateTime.fromSeconds(4243),
    };
    const expected: FileFinderModificationTimeCondition = {
      minLastModifiedTime: '4242000000',
      maxLastModifiedTime: '4243000000',
    };
    expect(formValuesToFileFinderModificationTimeCondition(source))
        .toEqual(expected);
  });
});

describe('formValuesToFileFinderAccessTimeCondition()', () => {
  it('correctly converts empty form value', () => {
    const source: RawFormValues = {
      minTime: null,
      maxTime: null,
    };
    const expected: FileFinderAccessTimeCondition = {
      minLastAccessTime: undefined,
      maxLastAccessTime: undefined,
    };
    expect(formValuesToFileFinderAccessTimeCondition(source)).toEqual(expected);
  });

  it('correctly converts filled out form value', () => {
    const source: RawFormValues = {
      minTime: DateTime.fromSeconds(4242),
      maxTime: DateTime.fromSeconds(4243),
    };
    const expected: FileFinderAccessTimeCondition = {
      minLastAccessTime: '4242000000',
      maxLastAccessTime: '4243000000',
    };
    expect(formValuesToFileFinderAccessTimeCondition(source)).toEqual(expected);
  });
});

describe('formValuesToFileFinderInodeChangeTimeCondition()', () => {
  it('correctly converts empty form value', () => {
    const source: RawFormValues = {
      minTime: null,
      maxTime: null,
    };
    const expected: FileFinderInodeChangeTimeCondition = {
      minLastInodeChangeTime: undefined,
      maxLastInodeChangeTIme: undefined,
    };
    expect(formValuesToFileFinderInodeChangeTimeCondition(source))
        .toEqual(expected);
  });

  it('correctly converts filled out form value', () => {
    const source: RawFormValues = {
      minTime: DateTime.fromSeconds(4242),
      maxTime: DateTime.fromSeconds(4243),
    };
    const expected: FileFinderInodeChangeTimeCondition = {
      minLastInodeChangeTime: '4242000000',
      maxLastInodeChangeTIme: '4243000000',
    };
    expect(formValuesToFileFinderInodeChangeTimeCondition(source))
        .toEqual(expected);
  });
});
