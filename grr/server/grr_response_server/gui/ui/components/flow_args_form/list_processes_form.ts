import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Component, ElementRef, OnInit, Output, ViewChild} from '@angular/core';
import {FormControl, FormGroup, ValidatorFn} from '@angular/forms';
import {combineLatest} from 'rxjs';
import {map, shareReplay, startWith} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListProcessesArgs, NetworkConnectionState} from '../../lib/api/api_interfaces';

/** A form that configures the ListProcesses flow. */
@Component({
  templateUrl: './list_processes_form.ng.html',
  styleUrls: ['./list_processes_form.scss'],
})
export class ListProcessesForm extends
    FlowArgumentForm<ListProcessesArgs> implements OnInit {
  readonly CONNECTION_STATES = Object.values(NetworkConnectionState).sort();
  readonly SEPARATOR_KEY_CODES = [ENTER, COMMA, SPACE];

  readonly connectionStateAutocompleteControl = new FormControl();

  readonly controls = {
    pids: new FormControl([], integerArrayValidator()),
    filenameRegex: new FormControl(),
    connectionStates: new FormControl([]),
    fetchBinaries: new FormControl(),
  };
  readonly form = new FormGroup(this.controls);

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...values,
            pids: values.pids.map((pid: string) => Number(pid)),
          })),
      shareReplay(1),
  );

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  @ViewChild('connectionStateInputEl')
  connectionStateInputEl!: ElementRef<HTMLInputElement>;

  readonly autocompleteStates$ =
      combineLatest([
        this.connectionStateAutocompleteControl.valueChanges.pipe(
            startWith('')),
        // Update autocomplete to re-show connection state that was removed from
        // chips.
        this.form.get('connectionStates')!.valueChanges.pipe(startWith(null)),
      ]).pipe(map(([q]) => this.filterStates(q)));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }

  removeConnectionState(state: NetworkConnectionState) {
    const formInput = this.form.get('connectionStates')!;
    const states = formInput.value as NetworkConnectionState[];
    formInput.setValue(states.filter(st => st !== state));
  }

  addConnectionState(state: NetworkConnectionState) {
    const formInput = this.form.get('connectionStates')!;
    formInput.setValue([...formInput.value, state]);
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
            !this.form.get('connectionStates')!.value.includes(state));
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
