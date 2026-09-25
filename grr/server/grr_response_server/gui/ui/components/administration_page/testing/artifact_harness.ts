import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

import {ArtifactDetailsHarness} from '../../shared/testing/artifact_details_harness';

/** Harness for the Artifact component. */
export class ArtifactHarness extends ComponentHarness {
  static hostSelector = 'artifact';

  readonly artifactDetails = this.locatorForOptional(ArtifactDetailsHarness);
  readonly deleteButton = this.locatorForOptional(
    MatButtonHarness.with({
      text: /.*Delete.*/,
    }),
  );

  private readonly noArtifactDetails = this.locatorForOptional(
    '.no-artifact-details',
  );

  async hasArtifactDetails(): Promise<boolean> {
    return (await this.artifactDetails()) !== null;
  }

  async getNoArtifactDetails(): Promise<string | undefined> {
    const noArtifactDetails = await this.noArtifactDetails();
    if (noArtifactDetails === null) {
      return undefined;
    }
    return noArtifactDetails.text();
  }

  async hasDeleteButton(): Promise<boolean> {
    return (await this.deleteButton()) !== null;
  }
}
