import {ComponentHarness} from '@angular/cdk/testing';

import {FlowConfigurationHarness} from './flow_configuration_harness';
import {FlowDebuggingHarness} from './flow_debugging_harness';
import {FlowResultsHarness} from './flow_results_harness';

/** Harness for the FlowLogs component. */
export class FlowDetailsHarness extends ComponentHarness {
  static hostSelector = 'flow-details';

  private readonly resultsComponent =
    this.locatorForOptional(FlowResultsHarness);
  private readonly configurationComponent = this.locatorForOptional(
    FlowConfigurationHarness,
  );
  private readonly debuggingComponent =
    this.locatorForOptional(FlowDebuggingHarness);

  async hasResultsComponent(): Promise<boolean> {
    return !!(await this.resultsComponent());
  }

  async hasConfigurationComponent(): Promise<boolean> {
    return !!(await this.configurationComponent());
  }

  async hasDebuggingComponent(): Promise<boolean> {
    return !!(await this.debuggingComponent());
  }
}
