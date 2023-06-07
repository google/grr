import {BaseHarnessFilters, ComponentHarness, HarnessPredicate} from '@angular/cdk/testing';
import {MatLegacyInputHarness} from '@angular/material/legacy-input/testing';

import {DATE_TIME_FORMAT} from '../../../../components/form/date_time_input/date_time_input';
import {DateTime} from '../../../../lib/date_time';


/** Filters used when searching for the harness component. */
export interface DateTimeInputHarnessFilters extends BaseHarnessFilters {}

/** Harness used for tests involving the date-time-input component. */
export class DateTimeInputHarness extends ComponentHarness {
  static hostSelector = 'date-time-input';

  private async getInput(): Promise<MatLegacyInputHarness> {
    return this.locatorFor(MatLegacyInputHarness)();
  }

  static with(options: DateTimeInputHarnessFilters):
      HarnessPredicate<DateTimeInputHarness> {
    return new HarnessPredicate(DateTimeInputHarness, options);
  }

  async setValue(dateTime: DateTime): Promise<void> {
    const input = await this.getInput();
    await input.setValue(dateTime.setZone('utc').toFormat(DATE_TIME_FORMAT));
  }
}
