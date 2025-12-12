import {ComponentHarness, TestKey} from '@angular/cdk/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the SearchBox component. */
export class SearchBoxHarness extends ComponentHarness {
  static hostSelector = 'search-box';

  readonly formField = this.locatorFor(MatFormFieldHarness);
  readonly searchInput = this.locatorFor(MatInputHarness);
  readonly autocomplete = this.locatorFor(MatAutocompleteHarness);

  async getSearchInput(): Promise<MatInputHarness> {
    return this.searchInput();
  }

  async getInput(): Promise<MatInputHarness> {
    const formField = await this.formField();
    const input = await formField.getControl(MatInputHarness);
    return input!;
  }

  async sendEnterKey(): Promise<void> {
    const input = await this.searchInput();
    const host = await input.host();
    await host.sendKeys(TestKey.ENTER);
  }
}
