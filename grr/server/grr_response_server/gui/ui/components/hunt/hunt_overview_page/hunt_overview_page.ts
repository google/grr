import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, TrackByFunction} from '@angular/core';
import {MatCardModule} from '@angular/material/card';
import {RouterModule} from '@angular/router';
import {Observable} from 'rxjs';

import {ApiHunt} from '../../../lib/api/api_interfaces';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';

/** Page showing an overview of recent hunts. */
@Component({
  selector: 'app-hunt-overview-page',
  templateUrl: './hunt_overview_page.ng.html',
  styleUrls: ['./hunt_overview_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntOverviewPageLocalStore],
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
  ],
  standalone: true,
})
export class HuntOverviewPage {
  readonly hunts$: Observable<ReadonlyArray<ApiHunt>> =
      this.huntsStore.results$;

  constructor(private readonly huntsStore: HuntOverviewPageLocalStore) {
    huntsStore.setArgs({count: 20});
  }

  readonly trackHuntById: TrackByFunction<ApiHunt> = (index, item) =>
      item.huntId;
}
