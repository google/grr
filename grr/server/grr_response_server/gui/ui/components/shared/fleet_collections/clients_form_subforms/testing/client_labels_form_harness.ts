import {ComponentHarness} from '@angular/cdk/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

/** Harness for the ClientLabelsForm component. */
export class ClientLabelsFormHarness extends ComponentHarness {
  static hostSelector = 'client-labels-form';

  readonly matchMode = this.locatorFor(MatSelectHarness);

  readonly addLabelButton = this.locatorFor(
    MatButtonHarness.with({text: /Add another label/}),
  );

  readonly labelNames = this.locatorForAll(MatInputHarness);
  readonly labelAutocompletes = this.locatorForAll(MatAutocompleteHarness);
  readonly removeLabelButtons = this.locatorForAll(
    MatButtonHarness.with({variant: 'icon', text: 'close'}),
  );

  async getLabelNames(): Promise<string[]> {
    const labelNames = await this.labelNames();
    return Promise.all(labelNames.map((labelName) => labelName.getValue()));
  }

  async getMatchMode(): Promise<string> {
    const matchMode = await this.matchMode();
    return matchMode.getValueText();
  }

  async setMatchMode(value: string): Promise<void> {
    const matchMode = await this.matchMode();
    await matchMode.clickOptions({text: value});
  }

  async getLabelAutocompleteOptions(index: number): Promise<string[]> {
    const autocompletes = await this.labelAutocompletes();
    const autocomplete = autocompletes[index];
    await autocomplete.focus();
    const options = await autocomplete.getOptions();
    return Promise.all(options.map((option) => option.getText()));
  }

  async removeLabel(index: number): Promise<void> {
    const removeLabelButtons = await this.removeLabelButtons();
    await removeLabelButtons[index].click();
  }

  async setLabel(index: number, value: string): Promise<void> {
    const labelNames = await this.labelNames();
    await labelNames[index].setValue(value);
  }
}
