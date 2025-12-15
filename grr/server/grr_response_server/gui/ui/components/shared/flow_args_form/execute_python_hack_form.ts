import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ExecutePythonHackArgs} from '../../../lib/api/api_interfaces';
import {translateDict} from '../../../lib/api/translation/primitive';
import {Binary} from '../../../lib/models/flow';
import {GlobalStore} from '../../../store/global_store';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls(validator: ValidatorFn) {
  return {
    hackName: new FormControl<string>('', [validator]),
    pyArgs: new FormArray<
      FormGroup<{
        key: FormControl<string>;
        value: FormControl<string>;
      }>
    >([]),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a ExecutePythonHack flow. */
@Component({
  selector: 'execute-python-hack-form',
  templateUrl: './execute_python_hack_form.ng.html',
  styleUrls: [
    './execute_python_hack_form.scss',
    './flow_args_form_styles.scss',
  ],
  imports: [
    CommonModule,
    FormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatSelectModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecutePythonHackForm extends FlowArgsFormInterface<
  ExecutePythonHackArgs,
  Controls
> {
  protected readonly globalStore = inject(GlobalStore);

  override makeControls(): Controls {
    return makeControls((control: AbstractControl): ValidationErrors | null => {
      if (
        control.value &&
        this.filteredHacks().find((h) => h.path === control.value)
      ) {
        return null;
      }

      // Invalid: The input does not match any hack in the list of available
      // python hacks.
      return {'optionNotSelected': true};
    });
  }

  constructor() {
    super();
    // Lazy load only when the form is opened, it should be a cheap call, in
    // case it causes delays in the UI we could fetch the binaries when the
    // global store is initialized.
    this.globalStore.fetchBinaryNames();
  }

  override convertFlowArgsToFormState(
    flowArgs: ExecutePythonHackArgs,
  ): ControlValues<Controls> {
    return {
      hackName: flowArgs.hackName ?? this.controls.hackName.defaultValue,
      pyArgs: Array.from(
        (
          translateDict(flowArgs.pyArgs ?? {}) as ReadonlyMap<string, string>
        ).entries(),
      ).map(([k, v]) => ({key: String(k), value: String(v)})),
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ExecutePythonHackArgs {
    return {
      hackName: formState.hackName ?? undefined,
      pyArgs: formState.pyArgs.length
        ? {
            dat: formState.pyArgs.map(({key, value}) => ({
              k: {string: key},
              v: {string: value},
            })),
          }
        : undefined,
    };
  }

  // TODO: As future UX improvement, we could highlight Python
  // hacks that match the current client OS, since Python hacks are "bound" to
  // one OS on upload.

  protected readonly filteredHacks = computed<Binary[]>(() => {
    return this.globalStore.pythonHacks().filter((h: Binary) => {
      const hackName = this.formValues()?.hackName;
      return h.path
        .toLowerCase()
        .includes(hackName ? hackName.toLowerCase() : '');
    });
  });

  selectHack(hackName: string) {
    this.controls.hackName.setValue(hackName);
  }

  override resetFlowArgs(flowArgs: ExecutePythonHackArgs): void {
    const formState = this.convertFlowArgsToFormState(flowArgs);
    for (let i = 0; i < formState.pyArgs.length; i++) {
      this.addKeyValueFormControl();
    }
    super.resetFlowArgs(flowArgs);
  }

  addKeyValueFormControl() {
    this.controls.pyArgs.push(
      new FormGroup({
        key: new FormControl('', {nonNullable: true}),
        value: new FormControl('', {nonNullable: true}),
      }),
    );
  }

  removeKeyValueFormControl(i: number) {
    this.controls.pyArgs.removeAt(i);
  }
}
