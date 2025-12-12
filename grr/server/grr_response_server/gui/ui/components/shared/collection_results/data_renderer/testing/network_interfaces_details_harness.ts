import {ComponentHarness, TestElement} from '@angular/cdk/testing';

import {DivHarness} from '../../../testing/div_harness';

/** Harness for the NetworkInterfacesDetails component. */
export class NetworkInterfacesDetailsHarness extends ComponentHarness {
  static hostSelector = 'network-interfaces-details';

  private readonly tables = this.locatorForAll('table');
  private readonly rows = this.locatorForAll('tr');
  private readonly noneText = this.locatorForOptional(
    DivHarness.with({text: 'None.'}),
  );

  async hasNoneText(): Promise<boolean> {
    return !!(await this.noneText());
  }

  async numTables(): Promise<number> {
    return (await this.tables()).length;
  }

  async getTables(): Promise<TestElement[]> {
    return await this.tables();
  }

  async numRows(): Promise<number> {
    return (await this.rows()).length;
  }

  async getRowTexts(): Promise<string[]> {
    const rows = await this.rows();
    const rowTexts: string[] = [];
    for (let i = 0; i < rows.length; i++) {
      rowTexts.push((await rows[i].text()).trim());
    }
    return rowTexts;
  }
}
