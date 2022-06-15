import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {TimelineArgs} from '../../lib/api/api_interfaces';
import {decodeBase64ToString, encodeStringToBase64} from '../../lib/api_translation/primitive';

function makeControls() {
  return {
    root: new FormControl<string>('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the timeline flow.
 */
@Component({
  selector: 'timeline-form',
  templateUrl: './timeline_form.ng.html',
  styleUrls: ['./timeline_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TimelineForm extends FlowArgumentForm<TimelineArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: TimelineArgs) {
    return {
      root: flowArgs.root ? decodeBase64ToString(flowArgs.root) :
                            this.controls.root.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      root: encodeStringToBase64(formState.root),
    };
  }
}
