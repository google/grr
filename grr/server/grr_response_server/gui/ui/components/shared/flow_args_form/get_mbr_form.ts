import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';

import {GetMBRArgs} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {};
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a GetMBR flow. */
@Component({
  selector: 'get-mbr-form',
  templateUrl: './get_mbr_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, SubmitButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GetMBRForm extends FlowArgsFormInterface<GetMBRArgs, Controls> {
  override makeControls(): Controls {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: GetMBRArgs,
  ): ControlValues<Controls> {
    return {};
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): GetMBRArgs {
    return {};
  }
}
