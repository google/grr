import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTooltipModule} from '@angular/material/tooltip';

import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../../shared/collapsible_container';
import {FleetCollectionProgressChart} from './fleet_collection_progress_chart';
import {FleetCollectionProgressTable} from './fleet_collection_progress_table';

/** Provides progress information for the current fleet collection. */
@Component({
  selector: 'fleet-collection-progress',
  templateUrl: './fleet_collection_progress.ng.html',
  styleUrls: ['./fleet_collection_progress.scss'],
  imports: [
    CollapsibleTitle,
    CollapsibleContainer,
    CollapsibleContent,
    CommonModule,
    FleetCollectionProgressChart,
    FleetCollectionProgressTable,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionProgress {
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);

  protected readonly fleetCollectionId = input<string>();

  protected readonly CollapsibleState = CollapsibleState;

  constructor() {
    this.fleetCollectionStore.pollFleetCollectionProgress(
      this.fleetCollectionId,
    );
  }

  protected readonly hasProgressData = computed(() => {
    const progress = this.fleetCollectionStore.fleetCollectionProgress();
    const startPoints = progress?.startPoints?.length ?? 0;
    const completePoints = progress?.completePoints?.length ?? 0;

    return startPoints > 0 || completePoints > 0;
  });

  protected getPercentage(part: bigint, all: bigint): bigint {
    if (all === BigInt(0)) return BigInt(0);

    return (part * BigInt(100)) / all;
  }
}
