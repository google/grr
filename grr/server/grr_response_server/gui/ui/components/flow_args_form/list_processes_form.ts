import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {ChangeDetectionStrategy, Component, ElementRef, ViewChild} from '@angular/core';
import {FormControl, ValidatorFn} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListProcessesArgs, NetworkConnectionState} from '../../lib/api/api_interfaces';

function makeControls() {
  return {
    pids: new FormControl<ReadonlyArray<number>>(
        [], {nonNullable: true, validators: [integerArrayValidator()]}),
    connectionStates: new FormControl<ReadonlyArray<NetworkConnectionState>>(
        [], {nonNullable: true}),
    filenameRegex: new FormControl('', {nonNullable: true}),
    fetchBinaries: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;


/** A form that configures the ListProcesses flow. */
@Component({
  selector: 'app-list-processes-form',
  templateUrl: './list_processes_form.ng.html',
  styleUrls: ['./list_processes_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ListProcessesForm extends
    FlowArgumentForm<ListProcessesArgs, Controls> {
  readonly CONNECTION_STATES = Object.values(NetworkConnectionState).sort();
  readonly SEPARATOR_KEY_CODES = [ENTER, COMMA, SPACE];

  readonly connectionStateAutocompleteControl = new FormControl();

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: ListProcessesArgs) {
    return {
      connectionStates: flowArgs.connectionStates ??
          this.controls.connectionStates.defaultValue,
      fetchBinaries:
          flowArgs.fetchBinaries ?? this.controls.fetchBinaries.defaultValue,
      filenameRegex:
          flowArgs.filenameRegex ?? this.controls.filenameRegex.defaultValue,
      pids: flowArgs.pids ?? this.controls.pids.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return formState;
  }

  @ViewChild('connectionStateInputEl')
  connectionStateInputEl!: ElementRef<HTMLInputElement>;

  readonly autocompleteStates$ =
      combineLatest([
        this.connectionStateAutocompleteControl.valueChanges.pipe(
            startWith('')),
        // Update autocomplete to re-show connection state that was removed from
        // chips.
        this.controls.connectionStates.valueChanges.pipe(startWith(null)),
      ]).pipe(map(([q]) => this.filterStates(q)));

  removeConnectionState(state: NetworkConnectionState) {
    const states =
        this.controls.connectionStates.value as NetworkConnectionState[];
    this.controls.connectionStates.setValue(states.filter(st => st !== state));
  }

  addConnectionState(state: NetworkConnectionState) {
    this.controls.connectionStates.setValue(
        [...this.controls.connectionStates.value, state]);
    this.connectionStateAutocompleteControl.setValue('');
    this.connectionStateInputEl.nativeElement.value = '';
  }

  tryAddAutocompleteConnectionState(state: string) {
    const results = this.filterStates(state);

    if (results.length === 1) {
      this.addConnectionState(results[0] as NetworkConnectionState);
      return;
    }

    const normalizedState = state.toUpperCase();

    if ((results as string[]).includes(normalizedState)) {
      this.addConnectionState(normalizedState as NetworkConnectionState);
    }
  }

  private filterStates(query?: string) {
    const normalizedQuery = (query ?? '').toUpperCase();
    return this.CONNECTION_STATES.filter(
        state => state.includes(normalizedQuery) &&
            !this.controls.connectionStates.value?.includes(state));
  }
}

function integerArrayValidator(): ValidatorFn {
  return (control) => {
    if (!control.value) {
      return null;
    }

    for (const entry of control.value) {
      if (!/^\d+$/.test(entry)) {
        return {'invalidIntegerEntry': {value: entry}};
      }
    }

    return null;
  };
}
