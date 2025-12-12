import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the ClientAddLabelDialog component. */
export class ClientAddLabelDialogHarness extends MatDialogHarness {
  static override hostSelector = 'client-add-label-dialog';

  readonly labelInput = this.locatorFor(MatInputHarness);
  readonly autocompleteInput = this.locatorFor(MatAutocompleteHarness);

  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel'}),
  );
  readonly addButton = this.locatorFor(MatButtonHarness.with({text: 'Add'}));

  async setInput(label: string): Promise<void> {
    return (await this.labelInput()).setValue(label);
  }

  async clickAddButton(): Promise<void> {
    return (await this.addButton()).click();
  }

  async isAddButtonDisabled(): Promise<boolean> {
    return (await this.addButton()).isDisabled();
  }

  async clickCancelButton(): Promise<void> {
    return (await this.cancelButton()).click();
  }

  async getSuggestedLabels(): Promise<string[]> {
    const autocompleteInput = await this.autocompleteInput();
    const autocompleteOptions = await autocompleteInput.getOptions();
    const suggestedLabels: string[] = [];
    for (const option of autocompleteOptions) {
      const optionText = await option.getText();
      if (
        optionText.includes('Add new label') ||
        optionText.includes('already present')
      ) {
        continue;
      }
      suggestedLabels.push(optionText);
    }
    return suggestedLabels;
  }

  async getIsNewLabelOptionVisible(): Promise<boolean> {
    const autocompleteInput = await this.autocompleteInput();
    const autocompleteOptions = await autocompleteInput.getOptions();
    for (const option of autocompleteOptions) {
      if ((await option.getText()).includes('Add new label')) {
        return true;
      }
    }
    return false;
  }

  async getIsAlreadyPresentOptionVisible(): Promise<boolean> {
    const autocompleteInput = await this.autocompleteInput();
    const autocompleteOptions = await autocompleteInput.getOptions();
    for (const option of autocompleteOptions) {
      if ((await option.getText()).includes('already present')) {
        return true;
      }
    }
    return false;
  }
}
