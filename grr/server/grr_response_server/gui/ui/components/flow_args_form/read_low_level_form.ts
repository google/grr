import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ReadLowLevelArgs} from '../../lib/api/api_interfaces';

/**
 * A form that makes it possible to configure the read_low_level flow.
 */
@Component({
  selector: 'read_low_level-form',
  templateUrl: './read_low_level_form.ng.html',
  styleUrls: ['./read_low_level_form.scss'],
})
export class ReadLowLevelForm extends
    FlowArgumentForm<ReadLowLevelArgs> implements OnInit {
  // TODO: Add validators for path and length fields.
  readonly controls = {
    path: new FormControl(),
    length: new FormControl(),
    offset: new FormControl(),
  };
  readonly form = new FormGroup(this.controls);

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
