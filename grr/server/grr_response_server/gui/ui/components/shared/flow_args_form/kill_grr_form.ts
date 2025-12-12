import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';

import {EmptyFlowArgs} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {};
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a Kill GRR flow. */
@Component({
  selector: 'kill-grr-form',
  templateUrl: './kill_grr_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, SubmitButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KillGrrForm extends FlowArgsFormInterface<
  EmptyFlowArgs,
  Controls
> {
  override makeControls(): Controls {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: EmptyFlowArgs,
  ): ControlValues<Controls> {
    return {};
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): EmptyFlowArgs {
    return {};
  }
}
