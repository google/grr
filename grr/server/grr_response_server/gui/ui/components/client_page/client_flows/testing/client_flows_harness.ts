import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {
  MatListItemHarness,
  MatNavListHarness,
} from '@angular/material/list/testing';
import {
  MatMenuHarness,
  MatMenuItemHarness,
} from '@angular/material/menu/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

import {FlowStateIconHarness} from '../../../shared/testing/flow_state_icon_harness';
import {UserHarness} from '../../../shared/testing/user_harness';
import {FlowFilter} from '../client_flows';

/** Harness for the ClientFlows component. */
export class ClientFlowsHarness extends ComponentHarness {
  static hostSelector = 'client-flows';

  readonly flowFilterSelect = this.locatorFor(MatSelectHarness);
  readonly newFlowButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'New Flow'}),
  );
  // List of flows that are started on a client.
  readonly flowList = this.locatorFor(
    MatNavListHarness.with({
      selector: '.flow-list',
    }),
  );
  // List of scheduled flows on a client.
  readonly scheduledFlowList = this.locatorFor(
    MatNavListHarness.with({
      selector: '.scheduled-flow-list',
    }),
  );

  /** Selects the given flow filter option. */
  async selectFilterOption(option: FlowFilter): Promise<void> {
    await (await this.flowFilterSelect()).open();
    return (await this.flowFilterSelect()).clickOptions({text: option});
  }

  async getFlowListItems(): Promise<MatListItemHarness[]> {
    return (await this.flowList()).getItems();
  }

  async getFlowListItemTitle(index: number): Promise<string> {
    return (await this.getFlowListItems())[index].getTitle();
  }

  async getFlowListItemText(index: number): Promise<string | null> {
    return (await this.getFlowListItems())[index].getFullText();
  }

  async hasFlowListItemRobotIcon(index: number): Promise<boolean> {
    return !!(await (
      await this.getFlowListItems()
    )[index].getHarness(MatIconHarness.with({name: 'smart_toy'})));
  }

  async hasFlowListItemUserImage(index: number): Promise<boolean> {
    return !!(await (
      await this.getFlowListItems()
    )[index].getHarness(UserHarness));
  }

  async hasCopyLinkButton(index: number): Promise<boolean> {
    return !!(await (
      await this.getFlowListItems()
    )[index].getHarness(MatIconHarness.with({name: 'link'})));
  }

  async hasNestedFlowsButton(index: number): Promise<boolean> {
    const flowListItem = (await this.getFlowListItems())[index];
    return !!(await flowListItem.getHarnessOrNull(
      MatButtonHarness.with({selector: '[name=toggleNestedFlows]'}),
    ));
  }

  async clickNestedFlowsButton(index: number): Promise<void> {
    const flowListItem = (await this.getFlowListItems())[index];
    const nestedFlowsButton = await flowListItem.getHarness(
      MatButtonHarness.with({selector: '[name=toggleNestedFlows]'}),
    );
    await nestedFlowsButton.click();
  }

  async getFlowStateIcon(index: number): Promise<FlowStateIconHarness> {
    return (await this.getFlowListItems())[index].getHarness(
      FlowStateIconHarness,
    );
  }

  async hasFlowMenuButton(index: number): Promise<boolean> {
    const flowListItem = (await this.getFlowListItems())[index];
    return !!(await flowListItem.getHarnessOrNull(
      MatButtonHarness.with({selector: '[name=flowMenuButton]'}),
    ));
  }

  async clickFlowMenuButton(index: number): Promise<void> {
    const flowListItem = (await this.getFlowListItems())[index];
    const flowMenuButton = await flowListItem.getHarness(
      MatButtonHarness.with({selector: '[name=flowMenuButton]'}),
    );
    await flowMenuButton.click();
  }

  async getFlowMenuItems(index: number): Promise<MatMenuItemHarness[]> {
    const flowListItem = (await this.getFlowListItems())[index];
    const flowMenu = await flowListItem.getHarness(MatMenuHarness);

    if (!flowMenu) {
      throw new Error(`Flow menu button at index ${index} is not visible`);
    }
    return flowMenu.getItems();
  }

  async hasCancelFlowMenuItem(index: number): Promise<boolean> {
    const flowListItem = (await this.getFlowListItems())[index];
    const flowMenu = await flowListItem.getHarness(MatMenuHarness);
    const flowMenuItems = await flowMenu.getItems();

    for (const item of flowMenuItems) {
      if ((await item.getText()).includes('Cancel flow')) {
        return true;
      }
    }
    return false;
  }

  async clickCancelFlowMenuItem(index: number): Promise<void> {
    const flowListItem = (await this.getFlowListItems())[index];
    const flowMenu = await flowListItem.getHarness(MatMenuHarness);
    const flowMenuItems = await flowMenu.getItems();

    for (const item of flowMenuItems) {
      if ((await item.getText()).includes('Cancel flow')) {
        await item.click();
        return;
      }
    }
    throw new Error(`Cancel flow menu item not found`);
  }

  async clickDuplicateFlowMenuItem(index: number): Promise<void> {
    const flowListItem = (await this.getFlowListItems())[index];
    const flowMenu = await flowListItem.getHarness(MatMenuHarness);
    const flowMenuItems = await flowMenu.getItems();

    for (const item of flowMenuItems) {
      if ((await item.getText()).includes('Duplicate flow')) {
        await item.click();
        return;
      }
    }
    throw new Error(`Duplicate flow menu item not found`);
  }

  /** Returns the list items of the scheduled flows. */
  async getScheduledFlowListItems(): Promise<MatListItemHarness[]> {
    return (await this.scheduledFlowList()).getItems();
  }

  /** Returns the title of the scheduled flow at the given index. */
  async getScheduledFlowListItemTitle(index: number): Promise<string> {
    return (await this.getScheduledFlowListItems())[index].getTitle();
  }

  /** Returns the text of the scheduled flow at the given index. */
  async getScheduledFlowListItemText(index: number): Promise<string | null> {
    return (await this.getScheduledFlowListItems())[index].getFullText();
  }

  /** Returns whether the scheduled flow at the given index has a user image. */
  async hasScheduledFlowListItemUserImage(index: number): Promise<boolean> {
    return !!(await (
      await this.getScheduledFlowListItems()
    )[index].getHarness(UserHarness));
  }

  /**
   * Returns whether the scheduled flow at the given index has a copy link
   * button.
   */
  async hasCopyLinkForScheduledFlowButton(index: number): Promise<boolean> {
    return !!(await (
      await this.getScheduledFlowListItems()
    )[index].getHarness(MatIconHarness.with({name: 'link'})));
  }

  /**
   * Returns the pending approval progress icon for the scheduled flow at the
   * given index.
   */
  async getPendingApprovalProgressIcon(index: number): Promise<MatIconHarness> {
    return (await this.getScheduledFlowListItems())[index].getHarness(
      MatIconHarness.with({name: 'schedule'}),
    );
  }
}
