import {
  AbstractControl,
  FormControl,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import {map} from 'rxjs/operators';
import {toDurationString} from './duration_conversion';

/**
 * DurationFormControl for verification and augmenting durationInput fields.
 */
export class DurationFormControl extends FormControl {
  showError(): boolean {
    return this.invalid && (this.dirty || this.touched);
  }

  static defaultTimeValidator(allowZero = false, max?: number): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value === undefined) {
        return {'input_error': 'Invalid input'};
      }
      if (!allowZero && Number(control.value) === 0) {
        return {'input_error': 'Value "0" is not allowed'};
      }
      if (max && control.value > max) {
        return {'input_error': 'Input is greater than the max allowed'};
      }
      return null;
    };
  }

  readonly printableStringLong$ = this.valueChanges.pipe(
    map((seconds) => {
      if (seconds === undefined) return '';
      return toDurationString(Number(seconds), 'long');
    }),
  );
}
