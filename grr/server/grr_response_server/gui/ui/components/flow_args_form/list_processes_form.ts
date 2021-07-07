import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup, ValidatorFn} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {ListProcessesArgs} from '@app/lib/api/api_interfaces';
import {map, shareReplay} from 'rxjs/operators';

/** A form that configures the ListProcesses flow. */
@Component({
  templateUrl: './list_processes_form.ng.html',
  styleUrls: ['./list_processes_form.scss'],
})
export class ListProcessesForm extends
    FlowArgumentForm<ListProcessesArgs> implements OnInit {
  readonly form = new FormGroup({
    pids: new FormControl([], integerArrayValidator()),
    filenameRegex: new FormControl(''),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...values,
            pids: values.pids.map((pid: string) => Number(pid)),
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
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
