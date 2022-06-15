import {Component, OnDestroy} from '@angular/core';
import {AbstractControl, FormGroup} from '@angular/forms';
import {map} from 'rxjs/operators';

import {observeOnDestroy} from '../../lib/reactive';

/** ControlValueAccessor's onChange callback function. */
export type OnChangeFn<T> = (value: T) => void;

/** ControlValueAccessor's onTouched callback function. */
export type OnTouchedFn = () => void;

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
    T extends {[K in keyof T]: AbstractControl | undefined}> = {
  [K in keyof T]: T[K] extends AbstractControl ?
      // For basic {key: FormControl<X>()} mappings, the type is {key: X}.
      T[K]['value'] :
      T[K] extends undefined | infer C extends AbstractControl ?
      // For optional {key?: FormControl<X>()} mappings, the type is
      // {key: X|undefined}.
      C['value'] | undefined :
      never
};

/** Form component to configure arguments for a Flow. */
@Component({template: ''})
export abstract class FlowArgumentForm<
    FlowArgs extends {},
                     Controls extends {[K in keyof Controls]: AbstractControl}>
    implements OnDestroy {
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

  readonly controls: Controls = this.makeControls();

  readonly form = new FormGroup<Controls>(this.controls, {updateOn: 'change'});

  readonly flowArgs$ = this.form.valueChanges.pipe(map(
      (values) =>
          this.convertFormStateToFlowArgs(values as ControlValues<Controls>)));

  readonly ngOnDestroy = observeOnDestroy(this);

  /** Returns the internal form state by converting API FlowArgs. */
  abstract convertFlowArgsToFormState(flowArgs: FlowArgs):
      ControlValues<Controls>;

  /**
   * Returns the FlowArgs to be passed to the API by converting internal
   * form state.
   */
  abstract convertFormStateToFlowArgs(formState: ControlValues<Controls>):
      FlowArgs;

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

  /**
   * Focus the first input element, e.g. by placing the cursor into the first
   * text input field.
   *
   * @param container This element's container element, can be used to
   *     conveniently querySelect() and focus nested input fields.
   */
  focus(container: HTMLElement): void {
    // Per default, focus the first input field or textarea.
    container.querySelector<HTMLElement>('input,textarea')?.focus();
  }
}
