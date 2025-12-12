import {Component, computed, effect, input} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {AbstractControl, FormGroup} from '@angular/forms';

import {FlowType} from '../../../lib/models/flow';

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
 *
 * Example 2: when `makeControls()` returns the type:
 *
 * ```
 * { key?: FormControl<string> }
 * ```
 *
 * `ControlValues<ReturnType<typeof makeControls>>` yields:
 *
 * ```
 * { key: string|undefined }
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

/** Form component to configure arguments for a Flow. */
@Component({template: ''})
export abstract class FlowArgsFormInterface<
  FlowArgs extends object,
  Controls extends {[K in keyof Controls]: AbstractControl},
> {
  /**
   * The flow arguments to pass to the form for display, if set the form will
   * be populated with the values and view only / disabled.
   */
  readonly initialFlowArgs = input<FlowArgs>();

  readonly editable = input<boolean>(true);

  readonly onSubmit = input<(flowName: string, flowArgs: FlowArgs) => void>(
    (flowName, flowArgs) => {},
  );

  /** The controls used for this form. */
  readonly controls: Controls = this.makeControls();
  /** The form group used for this form. */
  protected readonly form = new FormGroup<Controls>(this.controls, {
    updateOn: 'change',
  });

  /** The form values as a signal. */
  protected readonly formValues = toSignal(this.form.valueChanges);
  /** The form status as a signal. */
  protected readonly formStatus = toSignal(this.form.statusChanges);

  /** The flow arguments as a signal. */
  readonly flowArgs = computed(() =>
    this.convertFormStateToFlowArgs(
      this.formValues() as ControlValues<Controls>,
    ),
  );

  /** Whether the form is valid. */
  readonly isValid = computed(() => this.formStatus() === 'VALID');

  protected readonly FlowType = FlowType;

  constructor() {
    // Trigger a form validation, otherwise an initial valid state is not
    // detected.
    this.form.updateValueAndValidity();

    const resetFlowArgsEffect = effect(() => {
      const initialFlowArgs = this.initialFlowArgs();
      if (initialFlowArgs) {
        this.resetFlowArgs(initialFlowArgs);
      }
      // Destroying the effect after the first run. We are polling executed
      // flows so the fixed flow args object is periodically updated, which
      // would re-trigger the resetting of the form. This is not needed as the
      // flow args are not changing
      resetFlowArgsEffect.destroy();
    });
  }

  // Only ControlValueAccessor is not enough because it does not handle
  // validation.
  /**
   * Returns an object of FormControls.
   *
   * ```
   * return {
   *   filename: new FormControl(''),
   *   maxSize: new FormControl(0),
   * };
   * ```
   */
  abstract makeControls(): Controls;

  /** Returns the internal form state by converting API FlowArgs. */
  abstract convertFlowArgsToFormState(
    flowArgs: FlowArgs,
  ): ControlValues<Controls>;

  /**
   * Returns the FlowArgs to be passed to the API by converting internal
   * form state.
   */
  abstract convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): FlowArgs;

  /**
   * Resets the form with the given values and marks it as pristine.
   *
   * Override this function to change the initial form state depending on the
   * provided default flow arguments, e.g. by adding a FormControl to a
   * FormArrays for every provided in put value.
   */
  resetFlowArgs(flowArgs: FlowArgs) {
    this.form.reset();
    this.form.patchValue(this.convertFlowArgsToFormState(flowArgs));
    this.form.markAsPristine();
  }
}
