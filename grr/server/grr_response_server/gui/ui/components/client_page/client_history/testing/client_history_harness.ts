import {ComponentHarness} from '@angular/cdk/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {
  MatListItemHarness,
  MatNavListHarness,
} from '@angular/material/list/testing';

import {ClientHistoryEntryHarness} from './client_history_entry_harness';

/** Harness for the ClientHistory component. */
export class ClientHistoryHarness extends ComponentHarness {
  static hostSelector = 'client-history';

  readonly timeline = this.locatorFor(MatNavListHarness);
  private readonly clientSnapshot = this.locatorForOptional(
    ClientHistoryEntryHarness,
  );

  async getTimeline(): Promise<MatNavListHarness> {
    return this.timeline();
  }

  async getTimelineItems(): Promise<MatListItemHarness[]> {
    return (await this.timeline()).getItems();
  }

  async getTimelineItemTitle(index: number): Promise<string> {
    return (await this.getTimelineItems())[index].getTitle();
  }

  async getTimelineItemSubtitle(index: number): Promise<string | null> {
    return (await this.getTimelineItems())[index].getSecondaryText();
  }

  async getTimelineItemText(index: number): Promise<string | null> {
    return (await this.getTimelineItems())[index].getFullText();
  }

  async hasTimelineItemStartupInfoIcon(index: number): Promise<boolean> {
    return (await this.getTimelineItems())[index].hasHarness(
      MatIconHarness.with({name: 'rocket_launch'}),
    );
  }

  async isClientSnapshotVisible(): Promise<boolean> {
    return !!(await this.clientSnapshot());
  }
}
