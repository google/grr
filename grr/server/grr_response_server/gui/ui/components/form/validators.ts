import {AbstractControl, ValidationErrors, ValidatorFn} from '@angular/forms';

import {DateTime} from '../../lib/date_time';
import {isNonNull} from '../../lib/preconditions';


/** Checks that at least one of the given controls has a non-null value set. */
export function atLeastOneMustBeSet(controls: readonly AbstractControl[]):
    ValidatorFn {
  return (): ValidationErrors => {
    for (const c of controls) {
      if (isNonNull(c.value)) {
        return {};
      }
    }
    return {
      'atLeastOneMustBeSet': true,
    };
  };
}

/** Checks that 2 date-time-input controls values are in order. */
export function timesInOrder(
    first: AbstractControl, second: AbstractControl): ValidatorFn {
  return (): ValidationErrors => {
    if (!first.value || !second.value) {
      return {};
    }

    const firstTime = first.value as DateTime;
    const secondTime = second.value as DateTime;

    if (firstTime.toMillis() >= secondTime.toMillis()) {
      return {
        'timesNotInOrder': true,
      };
    }

    return {};
  };
}
