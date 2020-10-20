import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';

import {OsqueryArgs} from '../../lib/api/api_interfaces';
import {FormGroup, FormControl, Validators} from '@angular/forms';
import {shareReplay} from 'rxjs/operators';


/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./osquery_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryForm extends FlowArgumentForm<OsqueryArgs> implements OnInit {
  readonly form = new FormGroup({
    query: new FormControl(null, Validators.required),
    timeoutMillis: new FormControl(null, Validators.required),
    ignoreStderrErrors: new FormControl(null),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue(this.defaultFlowArgs);
  }
}
