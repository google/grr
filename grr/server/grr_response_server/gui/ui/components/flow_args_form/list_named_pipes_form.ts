import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListNamedPipesFlowArgs, PipeEndFilter, PipeTypeFilter} from '../../lib/api/api_interfaces';

/** A form that customizes the behaviour of named pipe collection flow. */
@Component({
  selector: 'list-named-pipes-form',
  templateUrl: './list_named_pipes_form.ng.html',
  styleUrls: ['./list_named_pipes_form.scss'],
})
export class ListNamedPipesForm extends
    FlowArgumentForm<ListNamedPipesFlowArgs> implements OnInit {
  readonly PipeTypeFilter = PipeTypeFilter;
  readonly PipeEndFilter = PipeEndFilter;

  readonly controls = {
    pipeNameRegex: new FormControl(),
    procExeRegex: new FormControl(),
    pipeTypeFilter: new FormControl(PipeTypeFilter.ANY_TYPE),
    pipeEndFilter: new FormControl(PipeEndFilter.ANY_END),
  };
  readonly form = new FormGroup(this.controls);

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
