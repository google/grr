import {ComponentHarness} from '@angular/cdk/testing';
import {MatTreeHarness} from '@angular/material/tree/testing';

/** Harness for the ArtifactDetails component. */
export class ArtifactDetailsHarness extends ComponentHarness {
  static hostSelector = 'artifact-details';

  readonly matTreeHarness = this.locatorFor(MatTreeHarness);

  private readonly artifactName = this.locatorFor('.name');

  private readonly references = this.locatorFor('.links');

  private readonly supportedOs = this.locatorFor('.os');

  private readonly documentation = this.locatorFor('.documentation');

  async getArtifactName(): Promise<string> {
    return (await this.artifactName()).text();
  }

  async getReferences(): Promise<string> {
    return (await this.references()).text();
  }

  async getSupportedOss(): Promise<string> {
    return (await this.supportedOs()).text();
  }

  async getDocumentation(): Promise<string> {
    return (await this.documentation()).text();
  }
}
