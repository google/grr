import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {NetstatArgs} from '@app/lib/api/api_interfaces';
import {shareReplay} from 'rxjs/operators';

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
  readonly form = new FormGroup({
    listeningOnly: new FormControl(),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
