import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the Codeblock component. */
export class CodeblockHarness extends ComponentHarness {
  static hostSelector = 'codeblock';

  private readonly lines = this.locatorForAll('span');

  async linesText(): Promise<string[]> {
    const lines = await this.lines();
    return Promise.all(lines.map((line) => line.text()));
  }
}
