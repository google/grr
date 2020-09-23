import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {ClientSearchFacade} from '@app/store/client_search_facade';
import {map} from 'rxjs/operators';

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

  /**
   * Table rows for the MatTable component.
   */
  readonly rows$ = this.clientSearchFacade.clients$.pipe(
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
      private readonly clientSearchFacade: ClientSearchFacade,
  ) {}

  ngOnInit() {
    this.query$.subscribe(query => {
      this.clientSearchFacade.searchClients(query);
    });
  }
}
