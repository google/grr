import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';

import {FlowArgsFormHarness} from '../../../shared/flow_args_form/testing/flow_args_form_harness';
import {CollapsibleContainerHarness} from '../../../shared/testing/collapsible_container_harness';

/** Harness for the ClientAddLabelDialog component. */
export class CreateFlowDialogHarness extends MatDialogHarness {
  static override hostSelector = 'create-flow-dialog';

  readonly backButton = this.locatorForOptional(
    MatButtonHarness.with({text: /arrow_back/}),
  );

  readonly autocompleteHarness = this.locatorForOptional(
    MatAutocompleteHarness,
  );

  readonly flowCategories = this.locatorForAll(CollapsibleContainerHarness);

  readonly disableRrgSupportCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: /Disable RRG support/}),
  );
  private readonly flowArgsForm = this.locatorForOptional(FlowArgsFormHarness);

  /**
   * Returns true if the autocomplete input is visible.
   */
  async showsAutocompleteInput(): Promise<boolean> {
    return !!(await this.autocompleteHarness());
  }

  /**
   * Returns true if the flow categories are visible.
   */
  async showsFlowCategories(): Promise<boolean> {
    return (await this.flowCategories()).length > 0;
  }
  /**
   * Returns true if the flow args form is visible.
   */
  async showsFlowArgsForm(): Promise<boolean> {
    return !!(await this.flowArgsForm());
  }

  /**
   * Returns the flow args form harness.
   */
  async getFlowArgsForm(): Promise<FlowArgsFormHarness> {
    const flowArgsForm = await this.flowArgsForm();
    if (!flowArgsForm) {
      throw new Error('Flow args form is not found');
    }
    return flowArgsForm;
  }

  async getFlowButton(regex: RegExp): Promise<MatButtonHarness> {
    return this.locatorFor(MatButtonHarness.with({text: regex}))();
  }

  /**
   * Returns true if the flow button is visible.
   */
  async hasFlowButton(regex: RegExp): Promise<boolean> {
    return !!(await this.locatorForOptional(
      MatButtonHarness.with({text: regex}),
    )());
  }

  async openFlowCategory(name: string): Promise<void> {
    const flowCategories = await this.flowCategories();
    for (const flowCategory of flowCategories) {
      if ((await flowCategory.getHeaderText()).includes(name)) {
        await flowCategory.expand();
        return;
      }
    }
    throw new Error(`Flow category "${name}" not found`);
  }
}
