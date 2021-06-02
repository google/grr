import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {ActivatedRoute, Params} from '@angular/router';
import {ClientSearchGlobalStore} from '@app/store/client_search_global_store';
import {Observable} from 'rxjs';
import {filter, map, skip} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';

/**
 * Component displaying the client search results.
 */
@Component({
  templateUrl: './client_search.ng.html',
  styleUrls: ['./client_search.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientSearch implements OnInit {
  private readonly query$ = this.route.queryParamMap.pipe(
      map(params => params.get('q') ?? ''),
  );

  readonly reason$: Observable<Params> = this.route.queryParamMap.pipe(
      map(params => params.get('reason')),
      filter(isNonNull),
      map((reason) => ({'reason': reason})),
  );

  /**
   * Table rows for the MatTable component.
   */
  readonly rows$ = this.clientSearchGlobalStore.clients$.pipe(
      skip(1),
      map(clients => clients.map((c) => ({
                                   clientId: c.clientId,
                                   fqdn: c.knowledgeBase.fqdn,
                                   lastSeenAt: c.lastSeenAt,
                                 }))),
  );

  /**
   * Table columns for the MatTable component.
   */
  readonly columns = ['clientId', 'fqdn', 'lastSeenAt'];

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientSearchGlobalStore: ClientSearchGlobalStore,
  ) {}

  ngOnInit() {
    this.query$.subscribe(query => {
      this.clientSearchGlobalStore.searchClients(query);
    });
  }
}
