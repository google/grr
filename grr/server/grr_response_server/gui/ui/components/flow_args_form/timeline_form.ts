import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {TimelineArgs} from '@app/lib/api/api_interfaces';
import {shareReplay} from 'rxjs/operators';

/**
 * A form that makes it possible to configure the timeline flow.
 */
@Component({
  selector: 'timeline-form',
  templateUrl: './timeline_form.ng.html',
  styleUrls: ['./timeline_form.scss'],
})
export class TimelineForm extends FlowArgumentForm<TimelineArgs> implements
    OnInit {
  readonly form = new FormGroup({
    root: new FormControl(),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
