import {MatInputHarness} from '@angular/material/input/testing';
import {MatRadioGroupHarness} from '@angular/material/radio/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ListDirectoryForm component. */
export class ListDirectoryFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'list-directory-form';

  private readonly collectionMethodRadioGroupHarness =
    this.locatorFor(MatRadioGroupHarness);

  private readonly pathInputHarness = this.locatorFor(
    MatInputHarness.with({placeholder: 'E.g.: /usr/me'}),
  );

  /** Selects the collection method. */
  async selectCollectionMethod(collectionMethod: string) {
    const collectionMethodRadioGroupHarness =
      await this.collectionMethodRadioGroupHarness();
    await collectionMethodRadioGroupHarness.checkRadioButton({
      label: collectionMethod,
    });
  }

  /** Gets the selected collection method. */
  async getCollectionMethod(): Promise<string | null> {
    const collectionMethodRadioGroupHarness =
      await this.collectionMethodRadioGroupHarness();
    return collectionMethodRadioGroupHarness.getCheckedValue();
  }

  /** Sets the path input. */
  async setPathInput(path: string) {
    const pathInputHarness = await this.pathInputHarness();
    await pathInputHarness.setValue(path);
  }

  /** Gets the path input. */
  async getPathInput(): Promise<string> {
    const pathInputHarness = await this.pathInputHarness();
    return pathInputHarness.getValue();
  }
}
