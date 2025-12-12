import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatBadgeModule} from '@angular/material/badge';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ApiHuntStateReason} from '../../lib/api/api_interfaces';
import {HuntState} from '../../lib/models/hunt';
import {checkExhaustive} from '../../lib/utils';

/**
 * Component displaying the state of a Fleet Collection in a material chip.
 */
@Component({
  selector: 'fleet-collection-state-chip',
  templateUrl: './fleet_collection_state_chip.ng.html',
  styleUrls: ['./fleet_collection_state_chip.scss'],
  imports: [
    CommonModule,
    MatBadgeModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionStateChip {
  readonly fleetCollectionState = input.required<HuntState>();
  readonly fleetCollectionStateReason = input.required<ApiHuntStateReason>();
  readonly fleetCollectionStateComment = input<string>();

  readonly resultsCount = input<bigint>();

  protected readonly checkExhaustive = checkExhaustive;
  protected readonly HuntState = HuntState;
  protected readonly StateReason = ApiHuntStateReason;
}
