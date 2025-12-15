import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, computed} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';

import {
  ListProcessesArgs,
  NetworkConnectionState,
} from '../../../lib/api/api_interfaces';
import {CommaSeparatedNumberValueAccessor} from '../form/comma_separated_input/comma_separated_value_accessor';
import {FormErrors, integerArrayValidator} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

/** All possible connection states. */
export const CONNECTION_STATES = Object.values(NetworkConnectionState).sort();

function makeControls() {
  return {
    pids: new FormControl<readonly number[]>([], {
      nonNullable: true,
      validators: [integerArrayValidator()],
    }),
    connectionStates: new FormControl<readonly NetworkConnectionState[]>([], {
      nonNullable: true,
    }),
    filenameRegex: new FormControl('', {nonNullable: true}),
    fetchBinaries: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** A form that configures the ListProcesses flow. */
@Component({
  selector: 'list-processes-form',
  templateUrl: './list_processes_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommaSeparatedNumberValueAccessor,
    CommonModule,
    FormErrors,
    FormsModule,
    MatAutocompleteModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListProcessesForm extends FlowArgsFormInterface<
  ListProcessesArgs,
  Controls
> {
  protected readonly SEPARATOR_KEY_CODES = [ENTER, COMMA, SPACE];

  readonly connectionStateInputControl = new FormControl();
  private readonly connectionStateInput = toSignal(
    this.connectionStateInputControl.valueChanges,
  );

  readonly connectionStateSuggestions = computed(() => {
    const uppercaseInput = (this.connectionStateInput() ?? '').toUpperCase();
    const selectedStates = this.formValues()?.connectionStates ?? [];
    return CONNECTION_STATES.filter(
      (state) =>
        state.includes(uppercaseInput) && !selectedStates.includes(state),
    );
  });

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ListProcessesArgs,
  ): ControlValues<Controls> {
    return {
      connectionStates:
        flowArgs.connectionStates ??
        this.controls.connectionStates.defaultValue,
      fetchBinaries:
        flowArgs.fetchBinaries ?? this.controls.fetchBinaries.defaultValue,
      filenameRegex:
        flowArgs.filenameRegex ?? this.controls.filenameRegex.defaultValue,
      pids: flowArgs.pids ?? this.controls.pids.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ListProcessesArgs {
    return formState;
  }

  removeConnectionState(state: NetworkConnectionState) {
    this.controls.connectionStates.setValue(
      this.controls.connectionStates.value.filter((st) => st !== state),
    );
  }

  addConnectionState(state: NetworkConnectionState) {
    const states = this.controls.connectionStates.value;
    if (states.includes(state)) {
      return;
    }
    this.controls.connectionStates.setValue([...states, state]);
    this.connectionStateInputControl.setValue('');
  }

  tryAddInputConnectionState(state: string, inputEl: HTMLInputElement) {
    const connectionState = state.toUpperCase() as NetworkConnectionState;
    if (CONNECTION_STATES.includes(connectionState)) {
      this.addConnectionState(connectionState);
      inputEl.value = '';
    }
  }
}
