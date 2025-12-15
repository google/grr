import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';

import {RolloutFormHarness} from '../../../shared/fleet_collections/testing/rollout_form_harness';

/** Harness for the ModifyFleetCollectionDialog component. */
export class ModifyFleetCollectionDialogHarness extends MatDialogHarness {
  static override hostSelector = 'modify-fleet-collection-dialog';

  readonly rolloutForm = this.locatorFor(RolloutFormHarness);

  readonly submitButton = this.locatorFor(
    MatButtonHarness.with({text: 'Submit'}),
  );

  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel'}),
  );
}
