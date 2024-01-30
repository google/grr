import {
  AbstractControl,
  FormControl,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';

/**
 * ByteFormControl for verification and extending byteInput fields.
 */
export class ByteFormControl extends FormControl {
  showError(): boolean {
    return this.invalid && (this.dirty || this.touched);
  }

  static byteValidator(allowZero = false): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value === undefined) {
        return {'input_error': 'Invalid input'};
      }
      if (!allowZero && Number(control.value) === 0) {
        return {'input_error': 'Value must be larger than "0"'};
      }
      return null;
    };
  }
}
