import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {RouterModule} from '@angular/router';

import {HuntState} from '../../../lib/models/hunt';
import {FriendlyFlowNamePipe} from '../../../pipes/flow_pipes/friendly_flow_name';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleTitle,
} from '../../shared/collapsible_container';
import {FleetCollectionStateChip} from '../../shared/fleet_collection_state_chip';
import {FleetCollectionArguments} from '../../shared/fleet_collections/fleet_collection_arguments';
import {FlowArgsForm} from '../../shared/flow_args_form/flow_args_form';
import {Timestamp} from '../../shared/timestamp';
import {User} from '../../shared/user';
import {
  ModifyFleetCollectionDialog,
  ModifyFleetCollectionDialogData,
} from './modify_fleet_collection_dialog';

/** Component that displays configuration of a single fleet collection. */
@Component({
  selector: 'fleet-collection-configuration',
  templateUrl: './fleet_collection_configuration.ng.html',
  styleUrls: ['./fleet_collection_configuration.scss'],
  imports: [
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    FleetCollectionArguments,
    FleetCollectionStateChip,
    FlowArgsForm,
    FriendlyFlowNamePipe,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatTooltipModule,
    RouterModule,
    Timestamp,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionConfiguration {
  readonly fleetCollectionStore = inject(FleetCollectionStore);
  private readonly dialog = inject(MatDialog);

  protected readonly HuntState = HuntState;

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collection > Configuration');
  }

  protected openModifyFleetCollectionDialog() {
    const safetyLimits =
      this.fleetCollectionStore.fleetCollection()?.safetyLimits;
    if (!safetyLimits) {
      throw new Error('Fleet collection does not have safety limits.');
    }
    const data: ModifyFleetCollectionDialogData = {
      currentSafetyLimits: safetyLimits,
      onSubmit: this.fleetCollectionStore.updateFleetCollection,
    };

    this.dialog.open(ModifyFleetCollectionDialog, {
      data,
      minWidth: '60vw',
      height: '70vh',
    });
  }
}
