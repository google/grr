import {
  BaseHarnessFilters,
  ComponentHarness,
  HarnessPredicate,
} from '@angular/cdk/testing';
import {MatDatepickerInputHarness} from '@angular/material/datepicker/testing';
import {MatTimepickerInputHarness} from '@angular/material/timepicker/testing';
import {FormErrorsHarness} from '../../../form/testing/form_validation_harness';
import {DivHarness} from '../../../testing/div_harness';

/** Harness for the TimeRangeSubform component. */
export class TimeRangeSubformHarness extends ComponentHarness {
  static hostSelector = 'time-range-subform';

  static with(
    options: BaseHarnessFilters,
  ): HarnessPredicate<TimeRangeSubformHarness> {
    return new HarnessPredicate(TimeRangeSubformHarness, options);
  }

  /** All form errors. */
  readonly formErrors = this.locatorForAll(FormErrorsHarness);

  /** From time input. */
  readonly fromTimeInput = this.locatorFor(
    MatTimepickerInputHarness.with({selector: '.from-time-picker'}),
  );

  /** From date input. */
  readonly fromDateInput = this.locatorFor(
    MatDatepickerInputHarness.with({selector: '.from-date-picker'}),
  );

  private readonly fromUTCString = this.locatorForOptional(
    DivHarness.with({text: /From \(UTC\):.*/}),
  );

  /** To time input. */
  readonly toTimeInput = this.locatorFor(
    MatTimepickerInputHarness.with({selector: '.to-time-picker'}),
  );

  /** To date input. */
  readonly toDateInput = this.locatorFor(
    MatDatepickerInputHarness.with({selector: '.to-date-picker'}),
  );

  private readonly toUTCString = this.locatorForOptional(
    DivHarness.with({text: /To \(UTC\):.*/}),
  );

  /** Sets the `to` date. */
  async setToDate(date: string) {
    const input = await this.toDateInput();
    await input.setValue(date);
  }

  /** Sets the `to` time. */
  async setToTime(time: string) {
    const input = await this.toTimeInput();
    await input.setValue(time);
  }

  /** Sets the `from` date. */
  async setFromDate(date: string) {
    const input = await this.fromDateInput();
    await input.setValue(date);
  }

  /** Sets the `from` time. */
  async setFromTime(time: string) {
    const input = await this.fromTimeInput();
    await input.setValue(time);
  }

  /** Gets the `from` time in UTC timezone displayed in the UI. */
  async getFromUTCString(): Promise<string | null> {
    const div = await this.fromUTCString();
    if (!div) {
      throw new Error('From UTC string is not present');
    }
    return div.getText() ?? null;
  }

  /** Gets the `to` time in UTC timezone displayed in the UI. */
  async getToUTCString(): Promise<string | null> {
    const div = await this.toUTCString();
    if (!div) {
      throw new Error('To UTC string is not present');
    }
    return div?.getText() ?? null;
  }

  /** Checks whether the form shows any errors. */
  async hasFormErrors(): Promise<boolean> {
    const errors = await this.formErrors();
    for (const error of errors) {
      if ((await error.getErrorMessages()).length > 0) {
        return true;
      }
    }
    return false;
  }
}
