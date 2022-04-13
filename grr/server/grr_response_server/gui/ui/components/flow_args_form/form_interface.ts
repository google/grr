import {Component, OnDestroy} from '@angular/core';
import {AbstractControl, UntypedFormControl, UntypedFormGroup} from '@angular/forms';
import {map} from 'rxjs/operators';

import {observeOnDestroy} from '../../lib/reactive';

/** ControlValueAccessor's onChange callback function. */
export type OnChangeFn<T> = (value: T) => void;

/** ControlValueAccessor's onTouched callback function. */
export type OnTouchedFn = () => void;

/** Controls of a FlowArgumentForm. */
export type Controls<T extends {}> = {
  [key in keyof T] -?: UntypedFormControl
};

/** An object of AbstractControls (e.g. FormControl). */
export type AbstractControls<T extends {}> = {
  [key in keyof T] -?: AbstractControl
};

/** Form component to configure arguments for a Flow. */
@Component({template: ''})
export abstract class FlowArgumentForm<
    FlowArgs extends {},
    FormState extends {} = FlowArgs,
    C extends AbstractControls<FormState> = Controls<FormState>,> implements
    OnDestroy {
  // Only ControlValueAccessor is not enough because it does not handle
  // validation.
  /**
   * Returns an Object mapping from FormState keys to FormControls.
   *
   * ```
   * return {
   *   filename: new FormControl(),
   *   maxSize: new FormControl(),
   * };
   * ```
   */
  abstract makeControls(): C;

  readonly controls = this.makeControls();

  readonly form = new UntypedFormGroup(this.controls, {updateOn: 'change'});

  readonly flowArgs$ =
      this.form.valueChanges.pipe(map(this.convertFormStateToFlowArgs));

  readonly ngOnDestroy = observeOnDestroy(this);

  /** Returns the internal FormState by converting API FlowArgs. */
  abstract convertFlowArgsToFormState(flowArgs: FlowArgs): FormState;

  /**
   * Returns the FlowArgs to be passed to the API by converting internal
   * FormState.
   */
  abstract convertFormStateToFlowArgs(formState: FormState): FlowArgs;

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
