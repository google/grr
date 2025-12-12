import {ComponentHarness} from '@angular/cdk/testing';
import {OutputPluginsFormHarness} from './output_plugins_form_harness';

/** Harness for the FleetCollectionArguments component. */
export class FleetCollectionArgumentsHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-arguments';

  readonly outputPluginsForm = this.locatorForOptional(
    OutputPluginsFormHarness,
  );

  async getTextContent(): Promise<string> {
    return (await this.host()).text();
  }
}
