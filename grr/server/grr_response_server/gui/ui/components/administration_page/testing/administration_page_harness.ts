import {ComponentHarness} from '@angular/cdk/testing';

import {ArtifactsAdministrationHarness} from './artifacts_administration_harness';

/** Harness for the AdministrationPage component. */
export class AdministrationPageHarness extends ComponentHarness {
  static hostSelector = 'administration-page';

  private readonly artifactsAdministration = this.locatorFor(
    ArtifactsAdministrationHarness,
  );

  async isArtifactsAdministrationVisible(): Promise<boolean> {
    return !!(await this.artifactsAdministration());
  }
}
