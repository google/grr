import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';

/** Harness for the ExpandableHash component. */
export class ExpandableHashHarness extends ComponentHarness {
  static hostSelector = 'expandable-hash';

  private readonly button = this.locatorForOptional(MatButtonHarness);
  private readonly menu = this.locatorForOptional(MatMenuHarness);

  async hasButton(): Promise<boolean> {
    return !!(await this.button());
  }

  async getButton(): Promise<MatButtonHarness> {
    const button = await this.button();
    if (!button) {
      throw new Error('Button is not found');
    }
    return button;
  }

  async hasMenu(): Promise<boolean> {
    return !!(await this.menu());
  }

  async getMenu(): Promise<MatMenuHarness> {
    const menu = await this.menu();
    if (!menu) {
      throw new Error('Menu is not found');
    }
    return menu;
  }
}
