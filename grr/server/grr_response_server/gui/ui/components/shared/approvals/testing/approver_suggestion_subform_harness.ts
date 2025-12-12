import {ComponentHarness} from '@angular/cdk/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {
  MatChipGridHarness,
  MatChipInputHarness,
  MatChipRowHarness,
} from '@angular/material/chips/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';

/** Harness for the ApproverSuggestionSubform component. */
export class ApproverSuggestionSubformHarness extends ComponentHarness {
  static hostSelector = 'approver-suggestion-subform';

  private readonly approversFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Approvers'}),
  );

  private readonly approversChipGrid = this.locatorFor(MatChipGridHarness);
  readonly approversAutocomplete = this.locatorFor(MatAutocompleteHarness);

  async getAutocompleteOptions(): Promise<string[]> {
    const autocomplete = await this.approversAutocomplete();
    await autocomplete.focus();
    await autocomplete.blur();
    const options = await autocomplete.getOptions();
    return Promise.all(options.map((option) => option.getText()));
  }

  async selectAutocompleteOption(text: string): Promise<void> {
    const autocomplete = await this.approversAutocomplete();
    await autocomplete.focus();
    await autocomplete.blur();
    await autocomplete.selectOption({text});
  }

  async getApproversInputHarness(): Promise<MatChipInputHarness> {
    const approversFormField = await this.approversFormField();
    const control = await approversFormField?.getControl(MatChipGridHarness);
    const input = await control?.getInput();
    if (!input) {
      throw new Error('Approvers input is not found');
    }
    return input;
  }

  async getApprovers(): Promise<string[]> {
    const chips: MatChipRowHarness[] = await (
      await this.approversChipGrid()
    ).getRows();
    return Promise.all(chips.map((chip) => chip.getText()));
  }
}
