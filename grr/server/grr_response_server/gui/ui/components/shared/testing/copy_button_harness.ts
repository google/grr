import {ContentContainerComponentHarness} from '@angular/cdk/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';

/** Harness for the CopyButton component. */
export class CopyButtonHarness extends ContentContainerComponentHarness {
  static hostSelector = 'copy-button';

  private readonly tooltip = this.locatorForOptional(MatTooltipHarness);

  private readonly checkIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'check'}),
  );
  private readonly copyIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'content_copy'}),
  );
  private readonly contents = this.locatorFor('.content');

  async isCheckIconVisible(): Promise<boolean> {
    return !!(await this.checkIcon());
  }

  async isCopyIconVisible(): Promise<boolean> {
    return !!(await this.copyIcon());
  }

  async getContentsText(): Promise<string> {
    return (await this.contents()).text();
  }

  async click(): Promise<void> {
    return (await this.contents()).click();
  }

  async isTooltipDisabled(): Promise<boolean> {
    const tooltip = await this.tooltip();
    if (!tooltip) {
      throw new Error('Tooltip not found.');
    }
    return tooltip.isDisabled();
  }

  async getTooltipText(): Promise<string> {
    const tooltip = await this.tooltip();
    if (!tooltip) {
      throw new Error('Tooltip not found.');
    }
    await tooltip.show();
    return tooltip.getTooltipText();
  }
}
