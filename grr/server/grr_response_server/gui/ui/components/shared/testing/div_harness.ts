import {
  BaseHarnessFilters,
  ComponentHarness,
  HarnessPredicate,
} from '@angular/cdk/testing';

interface DivHarnessFilters extends BaseHarnessFilters {
  /** Only find instances whose text matches the given value. */
  text?: string | RegExp;
}

/** Harness for the Div component. */
export class DivHarness extends ComponentHarness {
  static hostSelector = 'div';

  static with(options: DivHarnessFilters = {}): HarnessPredicate<DivHarness> {
    return new HarnessPredicate(DivHarness, options).addOption(
      'text',
      options.text,
      (harness, text) => {
        return HarnessPredicate.stringMatches(harness.getText(), text);
      },
    );
  }

  async getText(): Promise<string> {
    return await (await this.host()).text();
  }
}
