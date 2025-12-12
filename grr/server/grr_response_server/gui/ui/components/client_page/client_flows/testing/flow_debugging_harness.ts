import {ComponentHarness} from '@angular/cdk/testing';

import {FlowLogsHarness} from './flow_logs_harness';

/** Harness for the FlowDebugging component. */
export class FlowDebuggingHarness extends ComponentHarness {
  static hostSelector = 'flow-debugging';

  readonly flowLogs = this.locatorFor(FlowLogsHarness);
}
