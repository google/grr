import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';

import {FleetCollectionArgumentsHarness} from '../../../shared/fleet_collections/testing/fleet_collection_arguments_harness';
import {FlowArgsFormHarness} from '../../../shared/flow_args_form/testing/flow_args_form_harness';
import {FleetCollectionStateChipHarness} from '../../../shared/testing/fleet_collection_state_chip_harness';
import {UserHarness} from '../../../shared/testing/user_harness';
import {ModifyFleetCollectionDialogHarness} from './modify_fleet_collection_dialog_harness';

/** Harness for the FleetCollectionConfiguration component. */
export class FleetCollectionConfigurationHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-configuration';

  readonly generalInfoTable = this.locatorFor('table');
  readonly creator = this.locatorFor(UserHarness);
  readonly flowIdLink = this.locatorForOptional('.flow-link');
  readonly fleetCollectionLink = this.locatorForOptional(
    '.fleet-collection-link',
  );
  readonly flowArgsForm = this.locatorFor(FlowArgsFormHarness);
  readonly fleetCollectionArguments = this.locatorFor(
    FleetCollectionArgumentsHarness,
  );

  readonly fleetCollectionStateChip = this.locatorFor(
    FleetCollectionStateChipHarness,
  );

  readonly startFleetCollectionButton = this.locatorFor(
    MatButtonHarness.with({text: 'Start Fleet Collection'}),
  );
  readonly startFleetCollectionTooltip = this.locatorFor(
    MatTooltipHarness.with({selector: '.start-fleet-collection-container'}),
  );

  readonly modifyRolloutParametersButton = this.locatorFor(
    MatButtonHarness.with({text: 'Modify Rollout Parameters'}),
  );

  readonly modifyRolloutParametersTooltip = this.locatorFor(
    MatTooltipHarness.with({selector: '.modify-fleet-collection-container'}),
  );

  readonly modifyFleetCollectionDialog = this.locatorForOptional(
    ModifyFleetCollectionDialogHarness,
  );

  readonly cancelFleetCollectionButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel Fleet Collection'}),
  );

  readonly cancelFleetCollectionTooltip = this.locatorFor(
    MatTooltipHarness.with({selector: '.cancel-fleet-collection-container'}),
  );

  readonly accessTooltip = this.locatorFor(
    MatTooltipHarness.with({selector: '.access-container'}),
  );
}
