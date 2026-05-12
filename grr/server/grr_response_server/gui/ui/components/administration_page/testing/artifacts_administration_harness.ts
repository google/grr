import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatNavListHarness} from '@angular/material/list/testing';

/** Harness for the ArtifactsAdministration component. */
export class ArtifactsAdministrationHarness extends ComponentHarness {
  static hostSelector = 'artifacts-administration';

  readonly searchFormControl = this.locatorFor(MatInputHarness);
  readonly artifactList = this.locatorFor(MatNavListHarness);
  readonly createArtifactButton = this.locatorFor(
    MatButtonHarness.with({text: 'Create new artifact'}),
  );
}
