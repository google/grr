import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  Validators as FormValidators,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';

/**
 * A FormControl that can store warnings.
 */
export class FormControlWithWarnings extends FormControl {
  warnings = signal<Set<Validators>>(new Set<Validators>());
}

/**
 * Validators for form.
 */
export enum Validators {
  LITERAL_GLOB_EXPRESSION = 'literalGlobExpression',
  LITERAL_KNOWLEDGEBASE_EXPRESSION = 'literalKnowledgebaseExpression',
  REQUIRED_INPUT = 'requiredInput',
  AT_LEAST_ONE_MUST_BE_SET = 'atLeastOneMustBeSet',
  TIMES_NOT_IN_ORDER = 'timesNotInOrder',
  MIN_VALUE = 'minValue',
  MAX_VALUE = 'maxValue',
  INVALID_FILE_SIZE = 'invalidFileSize',
  INVALID_INTEGER_ENTRY = 'invalidIntegerList',
  WINDOWS_PATH = 'windowsPath',
}

/**
 * Error messages for the validators.
 */
export const errorMessages: {
  [key: string]: string;
} = {
  [Validators.REQUIRED_INPUT]: 'Input is required.',
  [Validators.AT_LEAST_ONE_MUST_BE_SET]: 'At least one input must be set.',
  [Validators.TIMES_NOT_IN_ORDER]: 'Times must be in order.',
  [Validators.MIN_VALUE]: '', // Message set via the validator.
  [Validators.MAX_VALUE]: '', // Message set via the validator.
  [Validators.INVALID_FILE_SIZE]: 'Invalid file size.',
  [Validators.INVALID_INTEGER_ENTRY]: 'Invalid integer list.',
};

/**
 * Warning messages for the validators.
 */
export const warningMessages: {
  [key: string]: string;
} = {
  [Validators.LITERAL_GLOB_EXPRESSION]:
    'This path uses `*/**` literally and will not evaluate any paths with glob expressions.',
  [Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION]:
    'This path uses `%%` literally and will not evaluate any `%%knowledgebase_expressions%%`.',
  [Validators.WINDOWS_PATH]: 'Windows path use `\\` instead of `/`.',
};

/**
 * Validator that checks if the input path uses any * and stores a warning if
 * it does.
 */
export function literalGlobExpressionWarning(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (control.pristine) {
      return null;
    }
    if (!(control instanceof FormControlWithWarnings)) {
      return null;
    }
    if (control.value && control.value.includes('*')) {
      control.warnings.set(
        new Set([...control.warnings(), Validators.LITERAL_GLOB_EXPRESSION]),
      );
    } else {
      const warnings = control.warnings();
      warnings.delete(Validators.LITERAL_GLOB_EXPRESSION);
      // Create a new set to trigger change detection.
      control.warnings.set(new Set(warnings));
    }
    // Return null to indicate that the control is still valid although it might
    // have a warning.
    return null;
  };
}

/**
 * Validator that checks if the input path uses %%.
 */
export function literalKnowledgebaseExpressionWarning(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (control.pristine) {
      return null;
    }
    if (!(control instanceof FormControlWithWarnings)) {
      return null;
    }

    if (control.value && control.value.includes('%%')) {
      control.warnings.set(
        new Set([
          ...control.warnings(),
          Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION,
        ]),
      );
    } else {
      const warnings = control.warnings();
      warnings.delete(Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION);
      // Create a new set to trigger change detection.
      control.warnings.set(new Set(warnings));
    }
    // Return null to indicate that the control is still valid although it might
    // have a warning.
    return null;
  };
}

/**
 * Validator that checks if the input path uses /, as Windows paths use \.
 */
export function windowsPathWarning(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (control.pristine) {
      return null;
    }
    if (!(control instanceof FormControlWithWarnings)) {
      return null;
    }
    if (control.value && control.value.includes('/')) {
      control.warnings.set(
        new Set([...control.warnings(), Validators.WINDOWS_PATH]),
      );
    } else {
      const warnings = control.warnings();
      warnings.delete(Validators.WINDOWS_PATH);
      // Create a new set to trigger change detection.
      control.warnings.set(new Set(warnings));
    }
    // Return null to indicate that the control is still valid although it might
    // have a warning.
    return null;
  };
}

/**
 * Validator that checks if the input is not empty.
 */
export function requiredInput(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const errors = FormValidators.required(control);
    if (errors) {
      return {
        [Validators.REQUIRED_INPUT]: {value: control.value},
      };
    }
    return null;
  };
}

/**
 * Validator that checks if the input is greater than or equal to the minimum.
 */
export function minValue(min: number): ValidatorFn {
  return (
    control: AbstractControl<number | null | undefined>,
  ): ValidationErrors | null => {
    const errors = FormValidators.min(min)(control);
    if (errors) {
      return {
        [Validators.MIN_VALUE]: {
          value: control.value,
          note: `Minimum value is ${min}.`,
        },
      };
    }
    return null;
  };
}

/**
 * Validator that checks if the input is less than or equal to the maximum.
 */
export function maxValue(max: number): ValidatorFn {
  return (
    control: AbstractControl<number | null | undefined>,
  ): ValidationErrors | null => {
    const errors = FormValidators.max(max)(control);
    if (errors) {
      return {
        [Validators.MAX_VALUE]: {
          value: control.value,
          note: `Maximum value is ${max}.`,
        },
      };
    }
    return null;
  };
}

/**
 * Validator that checks if at least one of the controls in the array is not
 * empty.
 */
export function atLeastOneControlMustBeSet(): ValidatorFn {
  return (
    control: AbstractControl<Array<string | null | undefined>>,
  ): ValidationErrors | null => {
    for (const c of (control as FormArray).controls) {
      if (c.value != null && c.value.trim() !== '') {
        return null;
      }
    }
    return {
      [Validators.AT_LEAST_ONE_MUST_BE_SET]: {value: null},
    };
  };
}

/** Checks that at least one of the given controls has a non-null value set. */
export function atLeastOneMustBeSet(
  controls: readonly AbstractControl[],
): ValidatorFn {
  return (
    control: AbstractControl<string | Date | number | null | undefined>,
  ): ValidationErrors | null => {
    for (const c of controls) {
      if (c.value != null) {
        return null;
      }
    }
    return {
      [Validators.AT_LEAST_ONE_MUST_BE_SET]: {value: null},
    };
  };
}

/**
 * Checks that 2 date-time-input controls values are in order.
 */
export function timesInOrder(
  first: AbstractControl<Date | null | undefined>,
  second: AbstractControl<Date | null | undefined>,
): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!first.value || !second.value) {
      return null;
    }
    if (first.value.getTime() >= second.value.getTime()) {
      return {
        [Validators.TIMES_NOT_IN_ORDER]: {value: [first.value, second.value]},
      };
    }

    return null;
  };
}

/**
 * Checks that the input is a comma-separated list of integers.
 */
export function integerArrayValidator(): ValidatorFn {
  return (
    control: AbstractControl<string | null | undefined>,
  ): ValidationErrors | null => {
    if (!control.value) {
      return null;
    }

    for (const entry of control.value) {
      if (!/^\d+$/.test(entry)) {
        return {[Validators.INVALID_INTEGER_ENTRY]: {value: control.value}};
      }
    }

    return null;
  };
}

/**
 * Component that displays error meesages for the validators.
 */
@Component({
  selector: 'form-errors',
  template: `@for (msg of reportedErrors(); track $index) {
    <span class="error">{{msg}}</span>
    @if (!$last) {
      <br />
    }
  }`,
  styleUrls: ['./form_validation.scss'],
  imports: [CommonModule, MatFormFieldModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FormErrors {
  validationErrors = input.required<ValidationErrors | null>();

  reportedErrors = computed((): string[] => {
    const validationErrors = this.validationErrors();
    if (!validationErrors) {
      return [];
    }
    const messages: string[] = [];
    for (const [key, value] of Object.entries(validationErrors)) {
      if (errorMessages.hasOwnProperty(key)) {
        messages.push(errorMessages[key] + String(value.note ?? ''));
      }
    }
    return messages;
  });
}

/**
 * Component that displays warnings messages for the validators.
 * Some validators indicate that the input is likely to be invalid but not
 * necessarily. In this case we do not want to show the error message but
 * instead show a warning message.
 */
@Component({
  selector: 'form-warnings',
  template: `@for (msg of reportedWarnings(); track msg) {
    <span class="warning">{{msg}}</span>
    @if (!$last) {
      <br />
    }
  }`,
  styleUrls: ['./form_validation.scss'],
  imports: [CommonModule, MatFormFieldModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FormWarnings {
  validationWarnings = input.required<Set<string>>();

  reportedWarnings = computed((): string[] => {
    const validationWarnings = this.validationWarnings();
    if (!validationWarnings) {
      return [];
    }
    const messages: string[] = [];
    for (const key of validationWarnings) {
      if (warningMessages.hasOwnProperty(key)) {
        messages.push(warningMessages[key]);
      }
    }
    return messages.sort();
  });
}
