
import {ChangeDetectionStrategy, Component, Input} from '@angular/core';

import {DateTimeInput} from '../../../components/form/date_time_input/date_time_input';


/** mat-form-field for GlobExpression inputs. */
@Component({
  selector: 'date-time-input-toggle',
  templateUrl: './date_time_input_toggle.ng.html',
  styleUrls: ['./date_time_input_toggle.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DateTimeInputToggle {
  @Input('for') dateTimeInput?: DateTimeInput;

  calendarClick() {
    if (this.dateTimeInput === undefined) {
      throw new Error(
          '[for] input must be specified on date-time-input-toggle');
    }

    this.dateTimeInput.calendarClick();
  }

  clockClick() {
    if (this.dateTimeInput === undefined) {
      throw new Error(
          '[for] input must be specified on date-time-input-toggle');
    }

    this.dateTimeInput.clockClick();
  }
}
