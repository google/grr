import {ComponentHarness} from '@angular/cdk/testing';

import {FlowArgsFormHarness} from '../../../shared/flow_args_form/testing/flow_args_form_harness';

/** Harness for the FlowConfiguration component. */
export class FlowConfigurationHarness extends ComponentHarness {
  static hostSelector = 'flow-configuration';

  readonly flowArgsForm = this.locatorForOptional(FlowArgsFormHarness);
}
