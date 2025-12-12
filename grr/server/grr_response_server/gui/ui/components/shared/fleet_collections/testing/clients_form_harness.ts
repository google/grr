import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCardHarness} from '@angular/material/card/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

import {ClientIntegerFormHarness} from '../clients_form_subforms/testing/client_integer_form_harness';
import {ClientLabelsFormHarness} from '../clients_form_subforms/testing/client_labels_form_harness';
import {ClientOsFormHarness} from '../clients_form_subforms/testing/client_os_form_harness';
import {ClientRegexFormHarness} from '../clients_form_subforms/testing/client_regex_form_harness';

/** Harness for the ClientsForm component. */
export class ClientsFormHarness extends ComponentHarness {
  static hostSelector = 'clients-form';

  readonly warningCard = this.locatorForOptional(MatCardHarness);
  readonly fixButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Fix/}),
  );

  readonly matchModeFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: /Match Mode/}),
  );
  readonly clientOsForms = this.locatorForAll(ClientOsFormHarness);
  readonly clientLabelsForms = this.locatorForAll(ClientLabelsFormHarness);
  readonly clientRegexForms = this.locatorForAll(ClientRegexFormHarness);
  readonly clientIntegerForms = this.locatorForAll(ClientIntegerFormHarness);

  readonly removeRuleButtons = this.locatorForAll(
    MatButtonHarness.with({selector: '.remove-rule-button'}),
  );

  readonly addConditionButton = this.locatorFor(
    MatButtonHarness.with({text: /Add Condition/}),
  );
  readonly addConditionMenu = this.locatorFor(MatMenuHarness);

  readonly resetButton = this.locatorFor(
    MatButtonHarness.with({text: 'Reset initial rules'}),
  );

  async getMatchMode(): Promise<string> {
    const matchModeFormField = await this.matchModeFormField();
    if (!matchModeFormField) {
      throw new Error('Match mode form field is not present');
    }
    const matchModeSelect =
      await matchModeFormField.getControl(MatSelectHarness);
    if (!matchModeSelect) {
      throw new Error('Match mode select is not present');
    }
    return matchModeSelect.getValueText();
  }

  async removeRuleButton(index: number): Promise<MatButtonHarness> {
    const removeRuleButtons = await this.removeRuleButtons();
    return removeRuleButtons[index];
  }
}
