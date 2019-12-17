import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {Observable} from 'rxjs';
import {filter, map, withLatestFrom} from 'rxjs/operators';

import {ApprovalConfig, ApprovalRequest, Client, ClientApproval} from '../lib/models/client';

import * as actions from './client/client_actions';
import {ClientState} from './client/client_reducers';
import * as selectors from './client/client_selectors';

/** Facade for client-related API calls. */
@Injectable()
export class ClientFacade {
  constructor(private readonly store: Store<ClientState>) {}

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> =
      this.store.select(selectors.clients)
          .pipe(
              withLatestFrom(this.store.select(selectors.selectedClientId)),
              map(([clients, clientId]) => clientId && clients[clientId]),
              filter((client): client is Client => client !== undefined),
          );

  /** Loads a client, marks it as selected, and emits it to selectedClient$. */
  selectClient(clientId: string): void {
    this.store.dispatch(actions.select({clientId}));
  }

  requestApproval(args: ApprovalRequest): void {
    this.store.dispatch(actions.requestApproval(args));
  }

  readonly approvalConfig$: Observable<ApprovalConfig|undefined> =
      this.store.select(selectors.approvalConfig);

  fetchApprovalConfig(): void {
    this.store.dispatch(actions.fetchApprovalConfig());
  }

  // Approvals are expected to be in reversed chronological order.
  readonly latestApproval$: Observable<ClientApproval|undefined> =
      this.store.select(selectors.approvals)
          .pipe(
              withLatestFrom(this.selectedClient$),
              map(([approvals, client]) => approvals.find(
                      approval => approval.clientId === client.clientId)),
          );

  listClientApprovals(clientId: string) {
    this.store.dispatch(actions.listApprovals({clientId}));
  }
}
