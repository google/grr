import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
} from '@angular/core';
import {
  ControlContainer,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {provideNativeDateAdapter} from '@angular/material/core';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatTimepickerModule} from '@angular/material/timepicker';
import {
  atLeastOneMustBeSet,
  FormErrors,
  timesInOrder,
} from '../../form/form_validation';

/** Form that configures a time range in UTC. */
@Component({
  selector: 'time-range-subform',
  templateUrl: './time_range_subform.ng.html',
  styleUrls: ['./time_range_subform.scss', 'subform_styles.scss'],
  providers: [provideNativeDateAdapter()],
  imports: [
    CommonModule,
    FormErrors,
    FormsModule,
    MatFormFieldModule,
    MatDatepickerModule,
    MatInputModule,
    MatTimepickerModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TimeRangeSubform implements OnInit {
  readonly controlContainer = inject(ControlContainer);

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createTimeRangeFormGroup
    >;
  }

  // TODO: Interete input as UTC time, this not yet supported
  // internally, waiting for
  // https://github.com/angular/components/tree/eba4719157a7f9a5d4f7a169a1323fd99564f3b6/src/material-moment-adapter/adapter
  //to be imported.

  // TODO: Workaround for bug with the datepicker/timepicker with
  // forms integration in reactive forms:
  // https://github.com/angular/angular/issues/58522.
  // Use
  // https://material.angular.dev/components/timepicker/overview#integration-with-matdatepicker
  // and
  // https://material.angular.dev/components/timepicker/overview#timepicker-forms-integration
  // instead when fixed.
  private fromTimeValue: Date | null = null;
  private toTimeValue: Date | null = null;

  set fromTime(newDate: Date | null) {
    if (newDate !== this.fromTimeValue) {
      this.fromTimeValue = newDate;
      this.formGroup.controls.fromTime.setValue(newDate);
    }
  }

  get fromTime() {
    return this.fromTimeValue;
  }

  set toTime(newDate: Date | null) {
    if (newDate !== this.toTimeValue) {
      this.toTimeValue = newDate;
      this.formGroup.controls.toTime.setValue(newDate);
    }
  }

  get toTime() {
    return this.toTimeValue;
  }

  ngOnInit() {
    // TODO: Manually sync the form values with the model. This is
    // only needed because of the workaround for the datepicker/timepicker bug.
    this.resetFormValues();
  }

  resetFormValues() {
    this.fromTimeValue = this.formGroup.controls.fromTime.value ?? null;
    this.toTimeValue = this.formGroup.controls.toTime.value ?? null;
  }
}

/** Initializes a form group corresponding to the time range form. */
export function createTimeRangeFormGroup() {
  const fromTime = new FormControl<Date | undefined>(undefined);
  const toTime = new FormControl<Date | undefined>(undefined);

  return new FormGroup(
    {'fromTime': fromTime, 'toTime': toTime},
    {
      validators: [
        atLeastOneMustBeSet([fromTime, toTime]),
        timesInOrder(fromTime, toTime),
      ],
    },
  );
}
