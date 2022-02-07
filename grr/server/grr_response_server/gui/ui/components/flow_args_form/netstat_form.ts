import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {NetstatArgs} from '../../lib/api/api_interfaces';

/**
 * A form that makes it possible to configure the netstat flow.
 */
@Component({
  selector: 'netstat-form',
  templateUrl: './netstat_form.ng.html',
  styleUrls: ['./netstat_form.scss'],
})
export class NetstatForm extends FlowArgumentForm<NetstatArgs> implements
    OnInit {
  readonly controls = {
    listeningOnly: new FormControl(),
  };
  readonly form = new FormGroup(this.controls);

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
