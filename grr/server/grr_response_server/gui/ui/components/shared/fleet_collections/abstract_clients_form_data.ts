import {AbstractControl, FormGroup} from '@angular/forms';
import {
  ForemanClientRule,
  ForemanClientRuleType,
} from '../../../lib/api/api_interfaces';

/**
 * The raw values of a Record of AbstractControls, e.g.:
 *
 * Example 1: when `makeControls()` returns:
 *
 * ```
 * { key: new FormControl('', {nonNullable: true}) }
 * ```
 *
 * `ControlValues<ReturnType<typeof makeControls>>` yields:
 *
 * ```
 * { key: string }
 * ```
 */
export declare type ControlValues<
  T extends {[K in keyof T]: AbstractControl | undefined},
> = {
  [K in keyof T]: T[K] extends AbstractControl
    ? // For basic {key: FormControl<X>()} mappings, the type is {key: X}.
      T[K]['value']
    : T[K] extends undefined | infer C extends AbstractControl
      ? // For optional {key?: FormControl<X>()} mappings, the type is
        // {key: X|undefined}.
        C['value'] | undefined
      : never;
};

/**
 * Abstract class for clients form data.
 */
export abstract class ClientsFormData<
  Controls extends {[K in keyof Controls]: AbstractControl},
> {
  type: ForemanClientRuleType | undefined = undefined;

  /** The controls used for this form. */
  readonly controls: Controls = this.makeControls();
  /** The form group used for this form. */
  readonly form = new FormGroup<Controls>(this.controls, {
    updateOn: 'change',
  });

  onChange: () => void = () => {};

  setOnChangeCallback(onChange: () => void) {
    this.onChange = onChange;
  }

  abstract makeControls(): Controls;

  abstract toClientRule(formValues: ControlValues<Controls>): ForemanClientRule;

  /**
   * Returns the ForemanClientRule representation of the form data.
   */
  getFormData(): ForemanClientRule {
    return this.toClientRule(this.form.value as ControlValues<Controls>);
  }
}
