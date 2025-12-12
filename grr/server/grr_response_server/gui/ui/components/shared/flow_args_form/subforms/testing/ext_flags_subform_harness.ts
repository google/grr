import {ComponentHarness} from '@angular/cdk/testing';
import {MatRadioGroupHarness} from '@angular/material/radio/testing';
import {DivHarness} from '../../../testing/div_harness';

/** Harness for the ExtFlagsSubform component. */
export class ExtFlagsSubformHarness extends ComponentHarness {
  static hostSelector = 'ext-flags-subform';

  private readonly linuxFlags = this.locatorForOptional(
    DivHarness.with({selector: '.linux-flags'}),
  );

  private readonly osxFlags = this.locatorForOptional(
    DivHarness.with({selector: '.macos-flags'}),
  );

  /** Selects the include radio button with the given label. */
  async selectIncludeFlag(label: string) {
    const radioGroup = await this.locatorFor(
      MatRadioGroupHarness.with({name: `ext-flags-${label}`}),
    )();
    await radioGroup.checkRadioButton({label: /Include*/});
  }

  /** Selects the exclude radio button with the given label. */
  async selectExcludeFlag(label: string) {
    const radioGroup = await this.locatorFor(
      MatRadioGroupHarness.with({name: `ext-flags-${label}`}),
    )();
    await radioGroup.checkRadioButton({label: /Exclude*/});
  }

  /** Selects the either radio button with the given label. */
  async selectEitherFlag(label: string) {
    const radioGroup = await this.locatorFor(
      MatRadioGroupHarness.with({name: `ext-flags-${label}`}),
    )();
    await radioGroup.checkRadioButton({label: /Include either*/});
  }

  /** Checks whether the Linux flags are visible. */
  async hasLinuxFlags() {
    return (await this.linuxFlags()) !== null;
  }

  /** Checks whether the macOS flags are visible. */
  async hasOsxFlags() {
    return (await this.osxFlags()) !== null;
  }

  /** Checks whether the flag with the given label is present. */
  async hasFlag(label: string) {
    const radioGroups = await this.locatorForAll(
      MatRadioGroupHarness.with({name: `ext-flags-${label}`}),
    )();
    return radioGroups.length > 0;
  }

  async getFlagSelection(label: string): Promise<string | null> {
    const radioGroups = await this.locatorForAll(
      MatRadioGroupHarness.with({name: `ext-flags-${label}`}),
    )();
    return radioGroups[0].getCheckedValue();
  }
}
