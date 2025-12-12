import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import {
  AbstractControl,
  FormControl,
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

import {LaunchBinaryArgs} from '../../../lib/api/api_interfaces';
import {Binary} from '../../../lib/models/flow';
import {GlobalStore} from '../../../store/global_store';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

// When receiving a list of binaries from the API, they do not include the
// prefix, but when scheduling a LaunchBinary flow, the prefix is required.
const REQUIRED_BINARY_PREFIX = 'aff4:/config/executables/';

function makeControls(validator: ValidatorFn) {
  return {
    binary: new FormControl<string>('', [validator]),
    commandLine: new FormControl('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a LaunchBinary flow. */
@Component({
  selector: 'launch-binary-form',
  templateUrl: './launch_binary_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
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
export class LaunchBinaryForm extends FlowArgsFormInterface<
  LaunchBinaryArgs,
  Controls
> {
  protected readonly globalStore = inject(GlobalStore);

  // TODO: As future UX improvement, we could highlight binaries
  // that match the current client OS, since binaries are "bound" to one OS on
  // upload.

  constructor() {
    super();
    // Lazy load only when the form is opened, it should be a cheap call, in
    // case it causes delays in the UI we could fetch the binaries when the
    // global store is initialized.
    this.globalStore.fetchBinaryNames();
  }

  override makeControls(): Controls {
    return makeControls((control: AbstractControl): ValidationErrors | null => {
      if (
        control.value &&
        this.filteredBinaries().find((h) => h.path === control.value)
      ) {
        return null;
      }

      // Invalid: The input does not match any hack in the list of available
      // python hacks.
      return {'optionNotSelected': true};
    });
  }

  override convertFlowArgsToFormState(
    flowArgs: LaunchBinaryArgs,
  ): ControlValues<Controls> {
    return {
      binary: flowArgs.binary
        ? flowArgs.binary.replace(REQUIRED_BINARY_PREFIX, '')
        : this.controls.binary.defaultValue,
      commandLine:
        flowArgs.commandLine ?? this.controls.commandLine.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): LaunchBinaryArgs {
    return {
      binary: formState.binary
        ? REQUIRED_BINARY_PREFIX + formState.binary
        : undefined,
      commandLine: formState.commandLine,
    };
  }

  protected readonly filteredBinaries = computed<Binary[]>(() => {
    return this.globalStore.executables().filter((h: Binary) => {
      const binary = this.formValues()?.binary;
      return h.path.toLowerCase().includes(binary ? binary.toLowerCase() : '');
    });
  });

  selectBinary(binary: string) {
    this.controls.binary.setValue(binary);
  }
}
