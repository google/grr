import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {Router} from '@angular/router';
import {map} from 'rxjs/operators';

import {Client} from '../../lib/models/client';
import {HomePageFacade} from '../../store/home_page_facade';

function uniqueClients(clients: ReadonlyArray<Client>): ReadonlyArray<Client> {
  const unique: Client[] = [];
  const foundIds = new Set();
  clients.forEach(client => {
    if (!foundIds.has(client.clientId)) {
      foundIds.add(client.clientId);
      unique.push(client);
    }
  });
  return unique;
}

/**
 * Provides the top-most component for the GRR UI home page.
 */
@Component({
  templateUrl: './home.ng.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home {
  constructor(
      private readonly router: Router,
      title: Title,
      private readonly homePageFacade: HomePageFacade,
  ) {
    title.setTitle('GRR');
  }

  readonly recentClients$ = this.homePageFacade.recentClientApprovals$.pipe(
      map(approvals => approvals.map(approval => approval.subject)),
      map(uniqueClients),
  );

  /**
   * Event handler for the search box. Gets triggered when a user initiates
   * the client search.
   */
  onQuerySubmitted(query: string) {
    this.router.navigate(['/clients'], {queryParams: {'q': query}});
  }
}
