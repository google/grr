import {AbstractControl} from '@angular/forms';
import {ByteFormControl} from './byte_form_control';

describe('ByteFormControl.byteValidator', () => {
  it('return error when byte set to 0 and zero not allowed', () => {
    expect(
      ByteFormControl.byteValidator(false)({
        value: 0,
      } as AbstractControl),
    ).toEqual({
      'input_error': 'Value must be larger than "0"',
    });
  });

  it('pass when duration set to 0 and zero allowed', () => {
    expect(
      ByteFormControl.byteValidator(true)({
        value: 0,
      } as AbstractControl),
    ).toEqual(null);
  });

  it('pass when input valid', () => {
    expect(
      ByteFormControl.byteValidator(true)({
        value: '10',
      } as AbstractControl),
    ).toEqual(null);
  });

  it('return error when input invalid', () => {
    expect(
      ByteFormControl.byteValidator(true)({
        value: undefined,
      } as AbstractControl),
    ).toEqual({'input_error': 'Invalid input'});
  });
});
