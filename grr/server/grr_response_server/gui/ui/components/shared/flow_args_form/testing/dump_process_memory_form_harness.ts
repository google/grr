import {MatButtonToggleGroupHarness} from '@angular/material/button-toggle/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the DumpProcessMemoryForm component. */
export class DumpProcessMemoryFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'dump-process-memory-form';

  private readonly processFilterModeHarness = this.locatorFor(
    MatButtonToggleGroupHarness,
  );
  private readonly processRegexInputHarness = this.locatorForOptional(
    MatInputHarness.with({placeholder: 'python\\d?'}),
  );
  private readonly pidsInputHarness = this.locatorForOptional(
    MatInputHarness.with({placeholder: '1, 42, 123'}),
  );
  private readonly allInputHarness = this.locatorForOptional(
    MatInputHarness.with({value: 'All processes, except the GRR process.'}),
  );

  /** Skip readonly regions checkbox. */
  readonly skipReadonlyRegionsCheckbox = this.locatorFor(
    MatCheckboxHarness.with({name: 'skip-readonly-regions'}),
  );

  /** Skip executable regions checkbox. */
  readonly skipExecutableRegionsCheckbox = this.locatorFor(
    MatCheckboxHarness.with({name: 'skip-executable-regions'}),
  );

  /** Skip special regions checkbox. */
  readonly skipSpecialRegionsCheckbox = this.locatorFor(
    MatCheckboxHarness.with({name: 'skip-special-regions'}),
  );

  /** Skip shared regions checkbox. */
  readonly skipSharedRegionsCheckbox = this.locatorFor(
    MatCheckboxHarness.with({name: 'skip-shared-regions'}),
  );

  /** Skip mapped files checkbox. */
  readonly skipMappedFilesCheckbox = this.locatorFor(
    MatCheckboxHarness.with({name: 'skip-mapped-files'}),
  );

  /** Sets the filter mode. */
  async setFilterMode(mode: 'Name' | 'PID' | 'All') {
    const filterModeHarness = await this.processFilterModeHarness();
    const filterModeButtonHarness = await filterModeHarness.getToggles({
      text: mode,
    });
    if (filterModeButtonHarness.length !== 1) {
      throw new Error(
        `Expected exactly one filter mode button for ${mode}, but found ${filterModeButtonHarness.length}`,
      );
    }
    await filterModeButtonHarness[0].check();
  }

  async getFilterMode(): Promise<string> {
    const filterModeHarness = await this.processFilterModeHarness();
    const filterModeButtonHarnesses = await filterModeHarness.getToggles();
    for (const filterModeButtonHarness of filterModeButtonHarnesses) {
      if (await filterModeButtonHarness.isChecked()) {
        return filterModeButtonHarness.getText();
      }
    }
    throw new Error('No filter mode button is checked');
  }

  /** Returns whether the PID input harness is present. */
  async hasPidInputHarness(): Promise<boolean> {
    const pidsInputHarness = await this.pidsInputHarness();
    return !!pidsInputHarness;
  }

  /** Returns the PID input harness. */
  async getPidInputHarness() {
    const pidsInputHarness = await this.pidsInputHarness();
    if (!pidsInputHarness) {
      throw new Error('PID input harness is not found');
    }
    return pidsInputHarness;
  }

  async hasRegexInputHarness(): Promise<boolean> {
    const regexInputHarness = await this.processRegexInputHarness();
    return !!regexInputHarness;
  }

  /** Returns the regex input harness. */
  async getRegexInputHarness(): Promise<MatInputHarness> {
    const regexInputHarness = await this.processRegexInputHarness();
    if (!regexInputHarness) {
      throw new Error('Regex input harness is not found');
    }
    return regexInputHarness;
  }

  /** Returns whether the all processes input harness is present. */
  async hasAllInputHarness(): Promise<boolean> {
    const allInputHarness = await this.allInputHarness();
    return !!allInputHarness;
  }

  /** Returns the all processes input harness. */
  async getAllInputHarness(): Promise<MatInputHarness> {
    const allInputHarness = await this.allInputHarness();
    if (!allInputHarness) {
      throw new Error('All input harness is not found');
    }
    return allInputHarness;
  }
}
