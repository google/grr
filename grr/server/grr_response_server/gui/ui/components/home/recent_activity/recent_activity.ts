import {ChangeDetectionStrategy, Component} from '@angular/core';
import {map} from 'rxjs/operators';

import {ClientApproval} from '../../../lib/models/client';
import {HomePageGlobalStore} from '../../../store/home_page_global_store';

function uniqueClientsApprovals(approvals: readonly ClientApproval[]):
    readonly ClientApproval[] {
  const unique: ClientApproval[] = [];
  const foundIds = new Set();
  approvals.forEach(approval => {
    const client = approval.subject;
    if (!foundIds.has(client.clientId)) {
      foundIds.add(client.clientId);
      unique.push(approval);
    }
  });
  return unique;
}

/**
 * Displays the recently accessed clients and their flows created by the user.
 */
@Component({
  selector: 'app-recent-activity',
  templateUrl: './recent_activity.ng.html',
  styleUrls: ['./recent_activity.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecentActivity {
  constructor(
      private readonly homePageGlobalStore: HomePageGlobalStore,
  ) {}

  readonly recentClientApprovals$ =
      this.homePageGlobalStore.recentClientApprovals$.pipe(
          map(uniqueClientsApprovals),
      );

  trackClient(index: number, approval: ClientApproval) {
    return approval.subject.clientId;
  }
}