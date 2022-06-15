import {ChangeDetectionStrategy, Component} from '@angular/core';

import {FlowArgumentForm} from './form_interface';

/** Fallback to display when no form is configured for a Flow. */
@Component({
  template: '',
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class FallbackFlowArgsForm<T extends {}> extends
    FlowArgumentForm<T, {}> {
  override makeControls() {
    return {};
  }

  override convertFlowArgsToFormState(flowArgs: T): T {
    return flowArgs;
  }

  override convertFormStateToFlowArgs(formState: {}): T {
    return formState as T;
  }
}
