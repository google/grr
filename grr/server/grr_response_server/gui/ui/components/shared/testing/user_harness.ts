import {ComponentHarness} from '@angular/cdk/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';

/** Harness for the User component. */
export class UserHarness extends ComponentHarness {
  static hostSelector = 'user';

  private readonly fallbackIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'account_circle'}),
  );
  private readonly profileImage = this.locatorForOptional('img');

  private readonly username = this.locatorForOptional('.username');

  /** Returns true if the fallback icon is displayed. */
  async hasFallbackIcon(): Promise<boolean> {
    return !!(await this.fallbackIcon());
  }

  /** Returns true if the profile image is displayed. */
  async hasProfileImage(): Promise<boolean> {
    return !!(await this.profileImage());
  }

  /** Returns the source of the profile image if it is displayed, otherwise null. */
  async getImageSrc(): Promise<string | null> {
    const image = await this.profileImage();
    return image ? image.getAttribute('src') : null;
  }

  /** Returns true if the username is displayed. */
  async hasUsername(): Promise<boolean> {
    return !!(await this.username());
  }

  /** Returns the username if it is displayed, otherwise throws an error. */
  async getUsername(): Promise<string | null> {
    const username = await this.username();
    if (!username) {
      throw new Error('Username is not displayed');
    }
    return username.text();
  }

  /** Returns the tooltip text if it is displayed, otherwise null. */
  async getTooltipText(): Promise<string | null> {
    const tooltip = await this.locatorForOptional(MatTooltipHarness)();
    if (!tooltip) {
      throw new Error('Tooltip is not displayed');
    }
    await tooltip.show();
    return tooltip.getTooltipText();
  }
}
