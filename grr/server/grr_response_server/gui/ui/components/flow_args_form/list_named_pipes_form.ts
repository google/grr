import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {ListNamedPipesFlowArgs, PipeEndFilter, PipeTypeFilter} from '@app/lib/api/api_interfaces';
import {shareReplay} from 'rxjs/operators';

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

  readonly form = new FormGroup({
    pipeNameRegex: new FormControl(),
    procExeRegex: new FormControl(),
    pipeTypeFilter: new FormControl(PipeTypeFilter.ANY_TYPE),
    pipeEndFilter: new FormControl(PipeEndFilter.ANY_END),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
