import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';

import {EmailOutputPluginFormHarness} from '../output_plugins_form_subforms/testing/email_output_plugin_form_harness';

/** Harness for the OutputPluginsForm component. */
export class OutputPluginsFormHarness extends ComponentHarness {
  static hostSelector = 'output-plugins-form';

  private readonly fieldset = this.locatorForOptional('fieldset');

  async isDisabled(): Promise<boolean> {
    const fieldset = await this.fieldset();
    if (!fieldset) {
      throw new Error('Fieldset not found');
    }
    return fieldset.getProperty('disabled') ?? false;
  }

  readonly addPluginMenu = this.locatorFor(
    MatMenuHarness.with({triggerText: 'Add output plugin'}),
  );

  readonly pluginForms = this.locatorForAll(
    EmailOutputPluginFormHarness,
  );

  readonly emailOutputPluginForms = this.locatorForAll(
    EmailOutputPluginFormHarness,
  );

  async removePluginButton(index: number): Promise<MatButtonHarness> {
    const removePluginButtons = await this.locatorForAll(
      MatButtonHarness.with({text: 'close'}),
    )();
    if (removePluginButtons.length <= index) {
      throw new Error(`No remove plugin button found at index ${index}`);
    }
    return removePluginButtons[index];
  }
}
