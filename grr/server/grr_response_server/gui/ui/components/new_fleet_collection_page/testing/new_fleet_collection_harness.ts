import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {ClientsFormHarness} from '../../shared/fleet_collections/testing/clients_form_harness';
import {OutputPluginsFormHarness} from '../../shared/fleet_collections/testing/output_plugins_form_harness';
import {RolloutFormHarness} from '../../shared/fleet_collections/testing/rollout_form_harness';
import {FlowArgsFormHarness} from '../../shared/flow_args_form/testing/flow_args_form_harness';
import {ErrorMessageHarness} from '../../shared/testing/error_message_harness';
import {FleetCollectionStateChipHarness} from '../../shared/testing/fleet_collection_state_chip_harness';
import {FlowStateIconHarness} from '../../shared/testing/flow_state_icon_harness';

/** Harness for the NewFleetCollection component. */
export class NewFleetCollectionHarness extends ComponentHarness {
  static hostSelector = 'new-fleet-collection';

  readonly errorMessage = this.locatorForOptional(ErrorMessageHarness);

  readonly titleFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Name your fleet collection'}),
  );

  readonly fleetCollectionStateChip = this.locatorForOptional(
    FleetCollectionStateChipHarness,
  );
  readonly flowStateIcon = this.locatorForOptional(FlowStateIconHarness);

  readonly flowArgsForm = this.locatorForOptional(FlowArgsFormHarness);

  readonly sourceSection = this.locatorForOptional('.source-section');
  readonly rolloutForm = this.locatorForOptional(RolloutFormHarness);
  readonly outputPluginsForm = this.locatorForOptional(
    OutputPluginsFormHarness,
  );
  readonly clientsForm = this.locatorForOptional(ClientsFormHarness);

  readonly createFleetCollectionButton = this.locatorFor(
    MatButtonHarness.with({text: 'Create Fleet Collection'}),
  );

  async titleInput(): Promise<MatInputHarness> {
    const formField = await this.titleFormField();
    return (await formField.getControl(MatInputHarness))!;
  }
}
