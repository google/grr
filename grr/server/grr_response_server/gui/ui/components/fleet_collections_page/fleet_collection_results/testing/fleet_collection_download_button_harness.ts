import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';

/** Harness for the FleetCollectionDownloadButton component. */
export class FleetCollectionDownloadButtonHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-download-button';

  private readonly downloadButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Download options .*/}),
  );
  private readonly downloadMenu = this.locatorForOptional(MatMenuHarness);

  async hasDownloadButton() {
    return !!(await this.downloadButton());
  }

  async openDownloadMenu() {
    const downloadMenu = await this.downloadMenu();
    if (!downloadMenu) {
      throw new Error('Download menu is not available');
    }
    await downloadMenu.open();
    return downloadMenu;
  }

  async getDownloadMenuItemTexts() {
    const downloadMenu = await this.downloadMenu();
    if (!downloadMenu) {
      throw new Error('Download menu is not available');
    }
    await downloadMenu.open();
    const items = await downloadMenu.getItems();
    return Promise.all(items.map((item) => item.getText()));
  }

  async hasDownloadMenuItem(text: string) {
    const downloadMenu = await this.downloadMenu();
    if (!downloadMenu) {
      throw new Error('Download menu is not available');
    }
    await downloadMenu.open();
    const items = await downloadMenu.getItems();
    return Promise.all(items.map((item) => item.getText())).then((texts) =>
      texts.includes(text),
    );
  }
}
