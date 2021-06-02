import {BaseHarnessFilters, ContentContainerComponentHarness, HarnessPredicate} from '@angular/cdk/testing';


/** Filters used when searching for the harness component. */
export interface ResultAccordionHarnessFilters extends BaseHarnessFilters {}

/** Harness used for tests involving the result-accordion component. */
export class ResultAccordionHarness extends ContentContainerComponentHarness {
  static hostSelector = 'result-accordion';

  private readonly getHeader = this.locatorFor('.header');

  static with(options: ResultAccordionHarnessFilters):
      HarnessPredicate<ResultAccordionHarness> {
    return new HarnessPredicate(ResultAccordionHarness, options);
  }

  async toggle(): Promise<void> {
    const header = await this.getHeader();
    await header.click();
  }
}
