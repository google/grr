import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the SplitPanel component. */
export class SplitPanelHarness extends ComponentHarness {
  static hostSelector = 'split-panel';

  gutter = this.locatorFor('.gutter');
  protected panel1 = this.locatorFor('.panel1');
  protected panel2 = this.locatorFor('.panel2');
  protected container = this.locatorFor('.split-container');

  /** Gets the current flex-basis percentage of the first panel. */
  async getPanel1SizePercent(): Promise<number | null> {
    const panel1 = await this.panel1();
    const flexBasis = await panel1.getCssValue('flex-basis');
    if (flexBasis) {
      return Number(flexBasis.replace('%', ''));
    }
    return null;
  }

  /** Gets the split direction. */
  async getDirection(): Promise<'horizontal' | 'vertical'> {
    const container = await this.container();
    const isHorizontal = await container.hasClass('horizontal');
    return isHorizontal ? 'horizontal' : 'vertical';
  }
}
