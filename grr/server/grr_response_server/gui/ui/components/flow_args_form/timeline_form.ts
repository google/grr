import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {TimelineArgs} from '../../lib/api/api_interfaces';
import {decodeBase64ToString, encodeStringToBase64} from '../../lib/api_translation/primitive';

/**
 * A form that makes it possible to configure the timeline flow.
 */
@Component({
  selector: 'timeline-form',
  templateUrl: './timeline_form.ng.html',
  styleUrls: ['./timeline_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class TimelineForm extends FlowArgumentForm<TimelineArgs> {
  override makeControls(): Controls<TimelineArgs> {
    return {
      root: new UntypedFormControl(),
    };
  }

  override convertFlowArgsToFormState(flowArgs: TimelineArgs): TimelineArgs {
    return {
      root: flowArgs.root ? decodeBase64ToString(flowArgs.root) : '',
    };
  }

  override convertFormStateToFlowArgs(formState: TimelineArgs): TimelineArgs {
    return {
      root: encodeStringToBase64(formState.root ?? ''),
    };
  }
}
