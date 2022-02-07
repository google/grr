import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Observable} from 'rxjs';
import {map, shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {TimelineArgs} from '../../lib/api/api_interfaces';
import {decodeBase64ToString, encodeStringToBase64} from '../../lib/api_translation/primitive';

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
  readonly controls = {
    root: new FormControl(),
  };
  readonly form = new FormGroup(this.controls);

  @Output()
  readonly formValues$: Observable<TimelineArgs> = this.form.valueChanges.pipe(
      map(values => ({
            ...values,
            root: encodeStringToBase64(values.root),
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue({
      ...this.defaultFlowArgs,
      root: this.defaultFlowArgs.root ?
          decodeBase64ToString(this.defaultFlowArgs.root) :
          '',
    });
  }
}
