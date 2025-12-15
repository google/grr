import {ComponentHarness} from '@angular/cdk/testing';
import {MatBadgeHarness} from '@angular/material/badge/testing';
import {MatChipHarness} from '@angular/material/chips/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';

/** Harness for the FleetCollectionStateChip component. */
export class FleetCollectionStateChipHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-state-chip';

  readonly chip = this.locatorForOptional(MatChipHarness);
  readonly icon = this.locatorFor(MatIconHarness);
  readonly badge = this.locatorForOptional(MatBadgeHarness);
  private readonly tooltip = this.locatorFor(MatTooltipHarness);

  async getTooltipText(): Promise<string> {
    const tooltip = await this.tooltip();
    await tooltip.show();
    return tooltip.getTooltipText();
  }

  async getChipText(): Promise<string | undefined> {
    const chip = await this.chip();
    return chip?.getText();
  }
}
