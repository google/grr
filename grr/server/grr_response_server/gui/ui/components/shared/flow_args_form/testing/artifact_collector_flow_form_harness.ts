import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {ArtifactDetailsHarness} from '../../testing/artifact_details_harness';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ArtifactCollectorFlowForm component. */
export class ArtifactCollectorFlowFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'artifact-collector-flow-form';

  readonly form = this.locatorFor(MatFormFieldHarness);
  readonly autocompleteHarness = this.locatorFor(MatAutocompleteHarness);

  readonly artifactDetailsHarness = this.locatorForOptional(
    ArtifactDetailsHarness,
  );
}
