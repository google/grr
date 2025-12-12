import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {
  MatMenuHarness,
  MatMenuItemHarness,
} from '@angular/material/menu/testing';
import {MatSlideToggleHarness} from '@angular/material/slide-toggle/testing';

/** Harness for the UserMenu component. */
export class UserMenuHarness extends ComponentHarness {
  static hostSelector = 'user-menu';

  readonly userButton = this.locatorForOptional(MatButtonHarness);

  readonly menu = this.locatorForOptional(MatMenuHarness);

  readonly darkModeToggle = this.locatorForOptional(MatSlideToggleHarness);

  async getMenuItems(): Promise<MatMenuItemHarness[]> {
    const menu = await this.menu();
    await menu!.open();
    return menu!.getItems();
  }

  async getMenuItem(index: number): Promise<MatMenuItemHarness> {
    const menuItems = await this.getMenuItems();

    if (index >= menuItems.length) {
      throw new Error(`Menu item at index ${index} not found`);
    }
    return menuItems[index];
  }
}
