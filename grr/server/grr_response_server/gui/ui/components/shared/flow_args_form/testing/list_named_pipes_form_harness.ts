import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ListNamedPipesForm component. */
export class ListNamedPipesFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'list-named-pipes-form';

  private readonly pipeNameInputHarness = this.locatorFor(
    MatInputHarness.with({selector: '[name="pipeNameRegex"]'}),
  );

  private readonly processExecutableInputHarness = this.locatorFor(
    MatInputHarness.with({selector: '[name="procExeRegex"]'}),
  );

  private readonly pipeTypeSelectHarness = this.locatorFor(
    MatSelectHarness.with({selector: '[name="pipeTypeFilter"]'}),
  );

  private readonly pipeEndSelectHarness = this.locatorFor(
    MatSelectHarness.with({selector: '[name="pipeEndFilter"]'}),
  );

  /** Sets the value of the pipe name input. */
  async setPipeNameInput(value: string): Promise<void> {
    const input = await this.pipeNameInputHarness();
    await input.setValue(value);
  }

  /** Gets the value of the pipe name input. */
  async getPipeNameInputText(): Promise<string> {
    const input = await this.pipeNameInputHarness();
    return input.getValue();
  }

  /** Sets the value of the process executable input. */
  async setProcessExecutableInput(value: string): Promise<void> {
    const input = await this.processExecutableInputHarness();
    await input.setValue(value);
  }

  /** Gets the value of the process executable input. */
  async getProcessExecutableInputText(): Promise<string> {
    const input = await this.processExecutableInputHarness();
    return input.getValue();
  }

  /** Selects the pipe type. */
  async selectPipeType(value: string): Promise<void> {
    const select = await this.pipeTypeSelectHarness();
    await select.clickOptions({text: value});
  }

  /** Gets the value of the pipe type input. */
  async getSelectedPipeType(): Promise<string> {
    const select = await this.pipeTypeSelectHarness();
    return select.getValueText();
  }

  /** Selects the pipe end. */
  async selectPipeEnd(value: string): Promise<void> {
    const select = await this.pipeEndSelectHarness();
    await select.clickOptions({text: value});
  }

  /** Gets the value of the pipe end input. */
  async getSelectedPipeEnd(): Promise<string> {
    const select = await this.pipeEndSelectHarness();
    return select.getValueText();
  }
}
