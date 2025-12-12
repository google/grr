import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';

import {InterrogateArgs} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {};
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a Interrogate flow. */
@Component({
  selector: 'interrogate-form',
  templateUrl: './interrogate_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, SubmitButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterrogateForm extends FlowArgsFormInterface<
  InterrogateArgs,
  Controls
> {
  override makeControls(): Controls {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: InterrogateArgs,
  ): ControlValues<Controls> {
    return {};
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): InterrogateArgs {
    return {};
  }
}
