import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {FlowListEntry} from '@app/lib/models/flow';
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

  requestApproval(request: ApprovalRequest): void {
    this.store.dispatch(actions.requestApproval({request}));
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
                      approval => approval.clientId === client.clientId &&
                          approval.status.type !== 'expired')),
          );

  listClientApprovals(clientId: string) {
    this.store.dispatch(actions.listApprovals({clientId}));
  }

  readonly flowListEntries$: Observable<ReadonlyArray<FlowListEntry>> =
      this.store.select(selectors.flowListEntries);

  startFlow(clientId: string, flowName: string, flowArgs: unknown) {
    this.store.dispatch(actions.startFlow({clientId, flowName, flowArgs}));
  }

  toggleFlowExpansion(flowId: string) {
    this.store.dispatch(actions.toggleFlowExpansion({flowId}));
  }

  cancelFlow(clientId: string, flowId: string) {
    this.store.dispatch(actions.cancelFlow({clientId, flowId}));
  }
}
