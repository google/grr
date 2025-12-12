import {ComponentHarness} from '@angular/cdk/testing';

import {CopyButtonHarness} from './copy_button_harness';

/** Harness for the Timestamp component. */
export class TimestampHarness extends ComponentHarness {
  static hostSelector = 'timestamp';

  private readonly timestamp = this.locatorForOptional(CopyButtonHarness);

  async hasTimestamp(): Promise<boolean> {
    return !!(await this.timestamp());
  }

  async getTimestampText(): Promise<string> {
    const timestamp = await this.timestamp();
    if (!timestamp) {
      throw new Error('Timestamp not found.');
    }
    return timestamp.getContentsText();
  }

  async showsRelativeTimestamp(relativeTimestamp: string): Promise<boolean> {
    const host = await this.host();
    const text = await host.text();
    return text.includes(relativeTimestamp);
  }

  async getCopyButton(): Promise<CopyButtonHarness> {
    const copyButtonHarness = await this.locatorFor(CopyButtonHarness)();
    if (!copyButtonHarness) {
      throw new Error('Copy button not found.');
    }
    return copyButtonHarness;
  }
}
