import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute, Params, Router} from '@angular/router';
import {Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {Client, isClientId} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientSearchLocalStore} from '../../store/client_search_local_store';

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

  protected readonly query$ = this.route.queryParamMap.pipe(
      takeUntil(this.ngOnDestroy.triggered$),
      map(params => params.get('q') ?? ''),
  );

  protected readonly clientLinkParams$: Observable<Params> =
      this.route.queryParamMap.pipe(
          takeUntil(this.ngOnDestroy.triggered$),
          map(params => params.get('reason')),
          filter(isNonNull),
          map((reason) => ({'reason': reason})),
      );

  /**
   * Table rows for the MatTable component.
   */
  protected readonly rows$ = this.clientSearchLocalStore.clients$.pipe(
      map(clients => clients?.map(toRow) ?? []));
  /**
   * Table columns for the MatTable component.
   */
  protected readonly columns =
      ['clientId', 'fqdn', 'users', 'labels', 'online', 'lastSeenAt'] as const;

  constructor(
      private readonly route: ActivatedRoute,
      protected readonly clientSearchLocalStore: ClientSearchLocalStore,
      private readonly router: Router,

  ) {
    this.query$.subscribe(query => {
      this.clientSearchLocalStore.searchClients(query);
    });
  }

  async onQuerySubmitted(query: string) {
    if (isClientId(query)) {
      await this.router.navigate(['/clients', query]);
    } else {
      await this.router.navigate(
          ['/clients'],
          {queryParams: {...this.route.snapshot.queryParams, 'q': query}});
    }
  }
}
