import {AbstractControl} from '@angular/forms';
import {DurationFormControl} from './duration_form_control';

describe('DurationFormControl', () => {
  it('return error when duration set to 0 and zero not allowed', () => {
    expect(
      DurationFormControl.defaultTimeValidator(false)({
        value: 0,
      } as AbstractControl),
    ).toEqual({
      'input_error': 'Value "0" is not allowed',
    });
  });

  it('pass when duration set to 0 and zero allowed', () => {
    expect(
      DurationFormControl.defaultTimeValidator(true)({
        value: 0,
      } as AbstractControl),
    ).toEqual(null);
  });

  it('pass when input valid', () => {
    expect(
      DurationFormControl.defaultTimeValidator(true)({
        value: '10',
      } as AbstractControl),
    ).toEqual(null);
  });

  it('return error when input invalid', () => {
    expect(
      DurationFormControl.defaultTimeValidator(true)({
        value: undefined,
      } as AbstractControl),
    ).toEqual({'input_error': 'Invalid input'});
  });

  it('pass when max is specified and value is less than max', () => {
    expect(
      DurationFormControl.defaultTimeValidator(
        false,
        10,
      )({
        value: 5,
      } as AbstractControl),
    ).toEqual(null);
  });

  it('fails when max is specified and value is greater than max', () => {
    expect(
      DurationFormControl.defaultTimeValidator(
        false,
        10,
      )({
        value: 15,
      } as AbstractControl),
    ).toEqual({'input_error': 'Input is greater than the max allowed'});
  });
});
