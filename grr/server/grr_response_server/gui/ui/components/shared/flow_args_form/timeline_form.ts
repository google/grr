import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {TimelineArgs} from '../../../lib/api/api_interfaces';
import {
  decodeBase64ToString,
  encodeStringToBase64,
} from '../../../lib/api/translation/primitive';
import {
  FormControlWithWarnings,
  FormWarnings,
  literalGlobExpressionWarning,
  literalKnowledgebaseExpressionWarning,
} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    root: new FormControlWithWarnings('', {
      nonNullable: true,
      validators: [
        literalKnowledgebaseExpressionWarning(),
        literalGlobExpressionWarning(),
      ],
    }),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the timeline flow.
 */
@Component({
  selector: 'timeline-form',
  templateUrl: './timeline_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormWarnings,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TimelineForm extends FlowArgsFormInterface<
  TimelineArgs,
  Controls
> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: TimelineArgs,
  ): ControlValues<Controls> {
    return {
      root: flowArgs.root
        ? decodeBase64ToString(flowArgs.root)
        : this.controls.root.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): TimelineArgs {
    return {
      root: encodeStringToBase64(formState.root),
    };
  }
}
