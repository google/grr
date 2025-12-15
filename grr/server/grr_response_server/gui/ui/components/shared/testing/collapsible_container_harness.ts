import {
  BaseHarnessFilters,
  ComponentHarness,
  HarnessPredicate,
} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';

/** Harness for the CollapsibleContainer component. */
export class CollapsibleContainerHarness extends ComponentHarness {
  static hostSelector = 'collapsible-container';

  static with(
    options: BaseHarnessFilters = {},
  ): HarnessPredicate<CollapsibleContainerHarness> {
    return new HarnessPredicate(CollapsibleContainerHarness, options);
  }

  private readonly content = this.locatorForOptional('.content');
  private readonly header = this.locatorFor('.header');
  readonly toggleButton = this.locatorFor(MatButtonHarness);

  private readonly expandIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'unfold_more'}),
  );
  private readonly collapseIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'unfold_less'}),
  );

  async showsExpandIcon(): Promise<boolean> {
    return !!(await this.expandIcon());
  }

  async showsCollapseIcon(): Promise<boolean> {
    return !!(await this.collapseIcon());
  }

  async getHeaderText(): Promise<string> {
    return (await this.header()).text();
  }

  async isContentVisible(): Promise<boolean> {
    return !!(await this.content());
  }

  async getContentText(): Promise<string> {
    return (await this.content())!.text();
  }

  async expand(): Promise<void> {
    const button = await this.toggleButton();
    if (await this.showsExpandIcon()) {
      await button.click();
    }
  }
}

/** Harness for the CollapsibleTitle component. */
export class CollapsibleTitleHarness extends ComponentHarness {
  static hostSelector = 'collapsible-title';

  async text(): Promise<string> {
    return (await this.host()).text();
  }
}
