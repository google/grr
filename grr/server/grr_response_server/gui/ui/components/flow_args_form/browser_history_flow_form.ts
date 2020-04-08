import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';

import {ApiBrowserHistoryFlowArgs} from '../../lib/api/api_interfaces';

/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'browser-history-flow-form',
  templateUrl: './browser_history_flow_form.ng.html',
  styleUrls: ['./browser_history_flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrowserHistoryFlowForm extends
    FlowArgumentForm<ApiBrowserHistoryFlowArgs> implements OnInit {
  readonly form = new FormGroup({
    collectChrome: new FormControl(),
    collectFirefox: new FormControl(),
    collectInternetExplorer: new FormControl(),
    collectOpera: new FormControl(),
    collectSafari: new FormControl(),
  });

  @Output() readonly formValues$ = this.form.valueChanges;

  ngOnInit() {
    this.form.setValue(this.defaultFlowArgs);
  }
}
