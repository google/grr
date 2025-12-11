import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatDialog} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatListModule} from '@angular/material/list';
import {MatMenuModule} from '@angular/material/menu';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {Router, RouterModule} from '@angular/router';

import {ApiListHuntsArgsRobotFilter} from '../../lib/api/api_interfaces';
import {FLOW_DETAILS_BY_TYPE} from '../../lib/data/flows/flow_definitions';
import {FlowType} from '../../lib/models/flow';
import {Hunt, HuntState} from '../../lib/models/hunt';
import {FleetCollectionsStore} from '../../store/fleet_collections_store';
import {GlobalStore} from '../../store/global_store';
import {CopyButton} from '../shared/copy_button';
import {FleetCollectionStateChip} from '../shared/fleet_collection_state_chip';
import {SplitPanel} from '../shared/split_panel/split_panel';
import {Timestamp} from '../shared/timestamp';
import {User} from '../shared/user';
import {NewFleetCollectionDialog} from './new_fleet_collection_dialog';

const INITIAL_COUNT = 100;
const INITIAL_CREATOR_FILTER = ApiListHuntsArgsRobotFilter.NO_ROBOTS;
const INITIAL_STATE_FILTER: HuntState | null = null;

/** Component that displays fleet collections. */
@Component({
  selector: 'fleet-collections-page',
  templateUrl: './fleet_collections_page.ng.html',
  styleUrls: ['./fleet_collections_page.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FleetCollectionStateChip,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatMenuModule,
    MatProgressBarModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RouterModule,
    SplitPanel,
    Timestamp,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FleetCollectionsStore],
})
export class FleetCollectionsPage {
  protected readonly globalStore = inject(GlobalStore);
  protected readonly fleetCollectionsStore = inject(FleetCollectionsStore);

  protected readonly dialog = inject(MatDialog);
  protected readonly router = inject(Router);

  protected readonly ApiListHuntsArgsRobotFilter = ApiListHuntsArgsRobotFilter;
  protected readonly HuntState = HuntState;

  readonly creatorFilterFormControl = new FormControl(INITIAL_CREATOR_FILTER);
  protected readonly triggerFilter = toSignal(
    this.creatorFilterFormControl.valueChanges,
    {initialValue: INITIAL_CREATOR_FILTER},
  );

  readonly stateFilterFormControl = new FormControl(INITIAL_STATE_FILTER, {
    nonNullable: true,
  });
  protected readonly stateFilter = toSignal(
    this.stateFilterFormControl.valueChanges,
    {initialValue: INITIAL_STATE_FILTER},
  );

  protected readonly searchFilterFormControl = new FormControl('', {
    nonNullable: true,
  });

  protected readonly count = signal<number>(INITIAL_COUNT);

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collections');

    this.fleetCollectionsStore.pollFleetCollections(
      computed(() => {
        const triggerFilter = this.triggerFilter();
        const stateFilter = this.stateFilter();
        return {
          count: this.count(),
          robotFilter: triggerFilter ?? undefined,
          stateFilter: stateFilter ?? undefined,
        };
      }),
    );
  }

  protected percentageCompleted(fleetCollection: Hunt) {
    if (!fleetCollection.allClientsCount) {
      return 0;
    }

    return Number(
      (fleetCollection.completedClientsCount * BigInt(100)) /
        fleetCollection.allClientsCount,
    );
  }

  protected fleetCollectionMatchesSearchFilter(fleetCollection: Hunt) {
    const searchFilter = this.searchFilterFormControl.value;
    return (
      searchFilter === '' ||
      fleetCollection.creator.includes(searchFilter) ||
      fleetCollection.huntId.includes(searchFilter) ||
      (fleetCollection.description || '').includes(searchFilter)
    );
  }

  protected fleetCollectionMatchesStateFilter(fleetCollection: Hunt) {
    // The server has one combined state (PAUSED) for NOT_STARTED and
    // REACHED_CLIENT_LIMIT, so the API response contains fleet collection with
    // both states. We want to distinguish between them then in the UI, so we
    // manually filter them again here.
    if (this.stateFilterFormControl.value == null) {
      return true;
    }
    return fleetCollection.state === this.stateFilterFormControl.value;
  }

  protected increaseFleetCollectionsCount(count: number) {
    this.count.set(this.count() + count);
  }

  protected isRestrictedFlow(flowType: FlowType | undefined) {
    if (!flowType) {
      return false;
    }
    return FLOW_DETAILS_BY_TYPE.get(flowType)?.restricted ?? false;
  }

  protected openNewFleetCollectionDialog() {
    this.dialog.open(NewFleetCollectionDialog);
  }
}
