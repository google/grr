import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {
  MatListItemHarness,
  MatNavListHarness,
} from '@angular/material/list/testing';
import {
  MatMenuHarness,
  MatMenuItemHarness,
} from '@angular/material/menu/testing';
import {MatProgressBarHarness} from '@angular/material/progress-bar/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

import {FleetCollectionStateChipHarness} from '../../shared/testing/fleet_collection_state_chip_harness';
import {UserHarness} from '../../shared/testing/user_harness';

/** Harness for the FleetCollectionsPage component. */
export class FleetCollectionsPageHarness extends ComponentHarness {
  static hostSelector = 'fleet-collections-page';

  readonly fleetCollectionList = this.locatorFor(MatNavListHarness);

  readonly moreFleetCollectionsButton = this.locatorForOptional(
    MatButtonHarness.with({text: /.*load 100 more.*/}),
  );

  readonly creatorFilterFormField = this.locatorFor(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter by creator',
    }),
  );
  readonly stateFilterFormField = this.locatorFor(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter by state',
    }),
  );
  readonly searchFilterFormField = this.locatorFor(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter by user, id, or description',
    }),
  );

  async getCreatorFilterSelect(): Promise<MatSelectHarness> {
    const formField = await this.creatorFilterFormField();
    return (await formField.getControl(MatSelectHarness))!;
  }

  async getStateFilterSelect(): Promise<MatSelectHarness> {
    const formField = await this.stateFilterFormField();
    return (await formField.getControl(MatSelectHarness))!;
  }

  async getSearchFilterInput(): Promise<MatInputHarness> {
    const formField = await this.searchFilterFormField();
    return (await formField.getControl(MatInputHarness))!;
  }

  async getFleetCollectionListItems(): Promise<MatListItemHarness[]> {
    return (await this.fleetCollectionList()).getItems();
  }

  async getFleetCollectionListItemTitle(index: number): Promise<string> {
    return (await this.getFleetCollectionListItems())[index].getTitle();
  }

  async getFleetCollectionListItemText(index: number): Promise<string | null> {
    return (await this.getFleetCollectionListItems())[index].getFullText();
  }

  async getFleetCollectionStateIcon(
    index: number,
  ): Promise<FleetCollectionStateChipHarness> {
    return (await this.getFleetCollectionListItems())[index].getHarness(
      FleetCollectionStateChipHarness,
    );
  }

  async hasFleetCollectionUserHarness(index: number): Promise<UserHarness> {
    return await (
      await this.getFleetCollectionListItems()
    )[index].getHarness(UserHarness);
  }

  async getFleetCollectionListItemProgressBar(
    index: number,
  ): Promise<MatProgressBarHarness> {
    return (await this.getFleetCollectionListItems())[index].getHarness(
      MatProgressBarHarness,
    );
  }

  async getFleetCollectionMenuButton(index: number): Promise<MatButtonHarness> {
    const flowListItem = (await this.getFleetCollectionListItems())[index];
    return flowListItem.getHarness(
      MatButtonHarness.with({text: /.*more_vert.*/}),
    );
  }

  async getFleetCollectionMenuItems(
    index: number,
  ): Promise<MatMenuItemHarness[]> {
    const flowListItem = (await this.getFleetCollectionListItems())[index];
    const flowMenu = await flowListItem.getHarness(MatMenuHarness);

    if (!flowMenu) {
      throw new Error(
        `Fleet collection menu button at index ${index} is not visible`,
      );
    }
    return flowMenu.getItems();
  }

  async getFleetCollectionDuplicateMenuItem(
    index: number,
  ): Promise<MatMenuItemHarness> {
    const menuButton = await this.getFleetCollectionMenuButton(index);
    await menuButton.click();
    const menuItems = await this.getFleetCollectionMenuItems(index);
    for (const menuItem of menuItems) {
      if ((await menuItem.getText()) === 'Duplicate fleet collection') {
        return menuItem;
      }
    }
    throw new Error(
      `Duplicate fleet collection menu item at index ${index} is not visible`,
    );
  }
}
