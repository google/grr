import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute, Params} from '@angular/router';
import {Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {Client} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientSearchGlobalStore} from '../../store/client_search_global_store';

function toRow(c: Client) {
  return {
    clientId: c.clientId,
    fqdn: c.knowledgeBase.fqdn,
    labels: c.labels.map(label => label.name),
    lastSeenAt: c.lastSeenAt,
    users: c.knowledgeBase.users?.map(user => user.username) ?? [],
    additionalUserCount:
        c.knowledgeBase.users?.length ? c.knowledgeBase.users.length - 1 : 0,
  };
}

/**
 * Component displaying the client search results.
 */
@Component({
  templateUrl: './client_search.ng.html',
  styleUrls: ['./client_search.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientSearch implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  private readonly query$ = this.route.queryParamMap.pipe(
      takeUntil(this.ngOnDestroy.triggered$),
      map(params => params.get('q') ?? ''),
  );

  readonly reason$: Observable<Params> = this.route.queryParamMap.pipe(
      takeUntil(this.ngOnDestroy.triggered$),
      map(params => params.get('reason')),
      filter(isNonNull),
      map((reason) => ({'reason': reason})),
  );

  /**
   * Table rows for the MatTable component.
   */
  readonly rows$ = this.clientSearchGlobalStore.clients$.pipe(
      map(clients => clients?.map(toRow) ?? []));

  /**
   * Table columns for the MatTable component.
   */
  readonly columns =
      ['clientId', 'fqdn', 'users', 'labels', 'online', 'lastSeenAt'];

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientSearchGlobalStore: ClientSearchGlobalStore,
  ) {
    this.query$.subscribe(query => {
      this.clientSearchGlobalStore.searchClients(query);
    });
  }
}
