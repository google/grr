import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {
  FormArray,
  FormControl,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';
import {
  atLeastOneControlMustBeSet,
  atLeastOneMustBeSet,
  FormControlWithWarnings,
  FormErrors,
  FormWarnings,
  integerArrayValidator,
  literalGlobExpressionWarning,
  literalKnowledgebaseExpressionWarning,
  maxValue,
  minValue,
  requiredInput,
  timesInOrder,
  Validators,
  windowsPathWarning,
} from './form_validation';
import {
  FormErrorsHarness,
  FormWarningsHarness,
} from './testing/form_validation_harness';

initTestEnvironment();

function createControl(
  value: Date | string | string[] | number | null,
): FormControlWithWarnings {
  const control = new FormControlWithWarnings(value, {nonNullable: true});
  control.markAsDirty();
  return control;
}

function createArrayControl(
  values: ReadonlyArray<string | null | undefined>,
): FormArray {
  return new FormArray(
    values.map((value) => new FormControl<string | null | undefined>(value)),
  );
}

describe('Form Validation', () => {
  describe('Literal Glob Expression Warning', () => {
    it('should return no warnings when the input is null', () => {
      const validator: ValidatorFn = literalGlobExpressionWarning();
      const control = createControl(null);
      validator(control);
      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return null when the input does not contain *', () => {
      const validator: ValidatorFn = literalGlobExpressionWarning();
      const control = createControl('some/path');
      validator(control);
      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return an error when the input contains *', () => {
      const validator: ValidatorFn = literalGlobExpressionWarning();
      const control = createControl('some/*/path');
      validator(control);
      expect(control.warnings()).toEqual(
        new Set<Validators>([Validators.LITERAL_GLOB_EXPRESSION]),
      );
    });

    it('should return an error when the input contains several *', () => {
      const validator: ValidatorFn = literalGlobExpressionWarning();
      const control = createControl('some/**/path');
      validator(control);
      expect(control.warnings()).toEqual(
        new Set<Validators>([Validators.LITERAL_GLOB_EXPRESSION]),
      );
    });
  });

  describe('Literal Knowledgebase Expression Validator', () => {
    it('should return null when the input is null', () => {
      const validator: ValidatorFn = literalKnowledgebaseExpressionWarning();
      const control = createControl(null);
      validator(control);
      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return null when the input does not contain %%', () => {
      const validator: ValidatorFn = literalKnowledgebaseExpressionWarning();
      const control = createControl('some/path');
      validator(control);
      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return an error when the input contains %%', () => {
      const validator: ValidatorFn = literalKnowledgebaseExpressionWarning();
      const control = createControl('some/path/with/%%/in/it');
      validator(control);
      expect(control.warnings()).toEqual(
        new Set<Validators>([Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION]),
      );
    });

    it('should return an error when the input contains several %%', () => {
      const validator: ValidatorFn = literalKnowledgebaseExpressionWarning();
      const control = createControl('some/path/with/%%in-it%%');
      validator(control);
      expect(control.warnings()).toEqual(
        new Set<Validators>([Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION]),
      );
    });
  });

  describe('Windows Path Warning', () => {
    it('should return no warnings when the input is null', () => {
      const validator: ValidatorFn = windowsPathWarning();

      const control = createControl(null);
      validator(control);

      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return no warnings when the input is a valid Windows path', () => {
      const validator: ValidatorFn = windowsPathWarning();

      const control = createControl('C:\\some\\path');
      validator(control);

      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return no warning when the input is a registry path', () => {
      const validator: ValidatorFn = windowsPathWarning();

      const control = createControl(
        'HKEY_CLASSES_ROOTCLSID{a3b9c5b6-5c92-4d1b-85e6-2f80b72f6f28}InProcServer32',
      );
      validator(control);

      expect(control.warnings()).toEqual(new Set<Validators>());
    });

    it('should return a warning when the input is a path with /', () => {
      const validator: ValidatorFn = windowsPathWarning();

      const control = createControl('C:/some/path');
      validator(control);

      expect(control.warnings()).toEqual(
        new Set<Validators>([Validators.WINDOWS_PATH]),
      );
    });
  });

  describe('Required Input Validator', () => {
    it('should return an error when the input is null', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl(null);
      expect(validator(control)).toEqual({
        [Validators.REQUIRED_INPUT]: {value: null},
      });
    });

    it('should return null when the input is not empty', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl('some/path');
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input contains several paths', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl('some/path\nanother/path');
      expect(validator(control)).toBeNull();
    });

    it('should return an error when the input is empty', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl('');
      expect(validator(control)).toEqual({
        'requiredInput': {value: ''},
      });
    });

    it('should return null for number input', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl(999);
      expect(validator(control)).toBeNull();
    });
  });

  describe('Minimum Value Validator', () => {
    it('should return null when the input is null', () => {
      const validator: ValidatorFn = minValue(0);
      const control = createControl(null);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input is valid', () => {
      const validator: ValidatorFn = minValue(0);
      const control = createControl(10);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input matches the minimum', () => {
      const validator: ValidatorFn = minValue(10);
      const control = createControl(10);
      expect(validator(control)).toBeNull();
    });

    it('should return an error when the input smaller than the minimum', () => {
      const validator: ValidatorFn = minValue(10);
      const control = createControl(0);
      expect(validator(control)).toEqual({
        [Validators.MIN_VALUE]: {value: 0, note: 'Minimum value is 10.'},
      });
    });

    it('should return null for number input', () => {
      const validator: ValidatorFn = requiredInput();
      const control = createControl(999);
      expect(validator(control)).toBeNull();
    });
  });

  describe('Maximum Value Validator', () => {
    it('should return null when the input is null', () => {
      const validator: ValidatorFn = maxValue(0);
      const control = createControl(null);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input is valid', () => {
      const validator: ValidatorFn = maxValue(10);
      const control = createControl(9);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input matches the maximum', () => {
      const validator: ValidatorFn = maxValue(10);
      const control = createControl(10);
      expect(validator(control)).toBeNull();
    });

    it('should return an error when the input is larger than the maximum', () => {
      const validator: ValidatorFn = maxValue(10);
      const control = createControl(11);
      expect(validator(control)).toEqual({
        [Validators.MAX_VALUE]: {value: 11, note: 'Maximum value is 10.'},
      });
    });
  });

  describe('At Least One Control Must Be Set Validator', () => {
    it('should return null when the input is not empty', () => {
      const validator: ValidatorFn = atLeastOneControlMustBeSet();

      const controls = createArrayControl([null, 'foo', null]);
      expect(validator(controls)).toBeNull();
    });

    it('should return an error when the input is empty', () => {
      const validator: ValidatorFn = atLeastOneControlMustBeSet();
      const controls = createArrayControl([null, '']);
      expect(validator(controls)).toEqual({
        [Validators.AT_LEAST_ONE_MUST_BE_SET]: {value: null},
      });
    });
  });

  describe('At Least One Must Be Set Validator', () => {
    it('should return an error when no input is set', () => {
      const validator: ValidatorFn = atLeastOneMustBeSet([]);
      expect(validator(createControl(null))).toEqual({
        [Validators.AT_LEAST_ONE_MUST_BE_SET]: {value: null},
      });
    });

    it('should return null when the input is not empty', () => {
      const controls = [
        createControl(null),
        createControl(new Date(2024, 1, 1)),
        createControl(null),
      ];
      const validator: ValidatorFn = atLeastOneMustBeSet(controls);
      expect(validator(controls[0])).toBeNull();
    });

    it('should return an error when the input is empty', () => {
      const controls = [createControl(null)];
      const validator: ValidatorFn = atLeastOneMustBeSet(controls);
      expect(validator(controls[0])).toEqual({
        [Validators.AT_LEAST_ONE_MUST_BE_SET]: {value: null},
      });
    });
  });

  describe('Times In Order Validator', () => {
    it('should return an error when the first time is after the second time', () => {
      const first = createControl(new Date(2024, 1, 1));
      const second = createControl(new Date(2023, 1, 1));
      const validator: ValidatorFn = timesInOrder(first, second);
      expect(validator(first)).toEqual({
        [Validators.TIMES_NOT_IN_ORDER]: {value: [first.value, second.value]},
      });
    });

    it('should return an error when the first time is equal to the second time', () => {
      const first = createControl(new Date(2024, 1, 1));
      const second = createControl(new Date(2024, 1, 1));
      const validator: ValidatorFn = timesInOrder(first, second);
      expect(validator(first)).toEqual({
        [Validators.TIMES_NOT_IN_ORDER]: {value: [first.value, second.value]},
      });
    });

    it('should return null when the first time is before the second time', () => {
      const first = createControl(new Date(2023, 1, 1));
      const second = createControl(new Date(2024, 1, 1));
      const validator: ValidatorFn = timesInOrder(first, second);
      expect(validator(first)).toBeNull();
    });
  });

  describe('Integer Array Validator', () => {
    it('should return null when the input is empty', () => {
      const validator: ValidatorFn = integerArrayValidator();
      const control = createControl([]);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input is a valid array of integers', () => {
      const validator: ValidatorFn = integerArrayValidator();
      const control = createControl(['1', '2', '3']);
      expect(validator(control)).toBeNull();
    });

    it('should return null when the input is a single integer', () => {
      const validator: ValidatorFn = integerArrayValidator();
      const control = createControl(['1']);
      expect(validator(control)).toBeNull();
    });

    it('should return an error when the input contains a non-integer', () => {
      const validator: ValidatorFn = integerArrayValidator();
      const control = createControl(['1', '2', '3', 'not-an-integer']);
      expect(validator(control)).toEqual({
        [Validators.INVALID_INTEGER_ENTRY]: {
          value: ['1', '2', '3', 'not-an-integer'],
        },
      });
    });

    it('should return an error when the input is a non-integer', () => {
      const validator: ValidatorFn = integerArrayValidator();
      const control = createControl(['not-an-integer']);
      expect(validator(control)).toEqual({
        [Validators.INVALID_INTEGER_ENTRY]: {value: ['not-an-integer']},
      });
    });
  });

  async function createFormErrorsComponent(
    formErrors: ValidationErrors | null,
  ) {
    const fixture = TestBed.createComponent(FormErrors);
    fixture.componentRef.setInput('validationErrors', formErrors);
    fixture.detectChanges();

    const harness = await TestbedHarnessEnvironment.harnessForFixture(
      fixture,
      FormErrorsHarness,
    );
    return {fixture, harness};
  }

  describe('Form Errors Component', () => {
    beforeEach(waitForAsync(() => {
      TestBed.configureTestingModule({
        imports: [NoopAnimationsModule, FormErrors],
        providers: [],
      }).compileComponents();
    }));

    it('renders no error for valid input', async () => {
      const {harness} = await createFormErrorsComponent(null);
      expect(await harness.getErrorMessages()).toEqual([]);
    });

    it('renders a single error messages', async () => {
      const {harness} = await createFormErrorsComponent({
        [Validators.REQUIRED_INPUT]: {value: ''},
      });
      expect(await harness.getErrorMessages()).toEqual(['Input is required.']);
    });

    it('renders multiple errors', async () => {
      const {harness} = await createFormErrorsComponent({
        [Validators.REQUIRED_INPUT]: {value: ''},
        [Validators.INVALID_FILE_SIZE]: {value: ''},
      });
      expect(await harness.getErrorMessages()).toEqual([
        'Input is required.',
        'Invalid file size.',
      ]);
    });
  });

  async function createFormWarningsComponent(warnings: Set<Validators>) {
    const fixture = TestBed.createComponent(FormWarnings);
    fixture.componentRef.setInput('validationWarnings', warnings);
    fixture.detectChanges();

    const harness = await TestbedHarnessEnvironment.harnessForFixture(
      fixture,
      FormWarningsHarness,
    );
    return {fixture, harness};
  }

  describe('Form Warnings Component', () => {
    beforeEach(waitForAsync(() => {
      TestBed.configureTestingModule({
        imports: [NoopAnimationsModule, FormWarnings],
        providers: [],
      }).compileComponents();
    }));

    it('renders no warning for valid input', async () => {
      const {harness} = await createFormWarningsComponent(
        new Set<Validators>(),
      );
      expect(await harness.getWarningMessages()).toEqual([]);
    });

    it('renders a single warning messages', async () => {
      const {harness} = await createFormWarningsComponent(
        new Set([Validators.LITERAL_GLOB_EXPRESSION]),
      );
      expect(await harness.getWarningMessages()).toEqual([
        'This path uses `*/**` literally and will not evaluate any paths with glob expressions.',
      ]);
    });

    it('renders multiple warnings', async () => {
      const {harness} = await createFormWarningsComponent(
        new Set([
          Validators.LITERAL_GLOB_EXPRESSION,
          Validators.LITERAL_KNOWLEDGEBASE_EXPRESSION,
        ]),
      );
      expect(await harness.getWarningMessages()).toEqual([
        'This path uses `%%` literally and will not evaluate any `%%knowledgebase_expressions%%`.',
        'This path uses `*/**` literally and will not evaluate any paths with glob expressions.',
      ]);
    });
  });
});
