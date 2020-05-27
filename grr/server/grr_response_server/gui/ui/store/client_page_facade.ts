import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {ConfigService} from '@app/components/config/config';
import {FlowDescriptor, FlowListEntry, FlowResultsQuery} from '@app/lib/models/flow';
import {combineLatest, interval, merge, Observable} from 'rxjs';
import {filter, ignoreElements, map, share, shareReplay, startWith, tap, withLatestFrom} from 'rxjs/operators';
import {ApprovalRequest, Client, ClientApproval} from '../lib/models/client';
import * as actions from './client_page/client_page_actions';
import {ClientPageState} from './client_page/client_page_reducers';
import * as selectors from './client_page/client_page_selectors';
import {ConfigFacade} from './config_facade';


/** Facade for client-related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientPageFacade {
  constructor(
      private readonly configService: ConfigService,
      private readonly store: Store<ClientPageState>,
      private readonly configFacade: ConfigFacade) {}

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

  updateFlows(clientId: string) {
    this.store.dispatch(actions.updateFlows({clientId}));
  }

  // This is a shared observable that exists only for side-effects (as it
  // does not emit values). When subscribed, it will periodically trigger
  // the "updateFlows" action on the store.
  private readonly intervalledFlowListEntriesUpdate$: Observable<void> =
      interval(this.configService.config.flowListPollingIntervalMs)
          .pipe(
              withLatestFrom(this.store.select(selectors.selectedClientId)),
              tap(([i, clientId]) => {
                if (clientId) {
                  this.store.dispatch(actions.updateFlows({clientId}));
                }
              }),
              ignoreElements(),
              share(),
          );

  // This is a shared observable that exists only for side-effects (as it
  // does not emit values). When subscribed, it will periodically trigger
  // the "batchListFlowResults" action on the store.
  private readonly intervalledFlowsResultsUpdate$: Observable<void> =
      interval(this.configService.config.flowResultsPollingIntervalMs)
          .pipe(
              withLatestFrom(
                  this.store.select(selectors.selectedClientId),
                  this.store.select(selectors.flowListEntryEntities),
                  ),
              tap(([i, clientId, flowListEntries]) => {
                if (clientId) {
                  this.store.dispatch(
                      actions.updateFlowsResults({clientId, flowListEntries}));
                }
              }),
              ignoreElements(),
              share(),
          );


  readonly flowListEntries$: Observable<ReadonlyArray<FlowListEntry>> =
      combineLatest(
          // Using combineLatest with intervalledFlowListEntriesUpdate ensures
          // that "updateFlows" and "updateResults" actions are periodically
          // triggered while the flowListEntries$ is subscribed.
          [
            merge(
                // We need to emit at least one value here, otherwise
                // combineLatest will never fire.
                this.intervalledFlowListEntriesUpdate$.pipe(startWith([0])),
                this.intervalledFlowsResultsUpdate$.pipe(startWith(0)),
                ),
            this.store.select(selectors.flowListEntries),
          ])
          .pipe(
              map(([unused, flowListEntries]) => flowListEntries),
          );

  startFlow(flowArgs: unknown) {
    this.store.dispatch(actions.startFlow({flowArgs}));
  }

  readonly startFlowState$ = this.store.select(selectors.startFlowState);

  toggleFlowExpansion(flowId: string) {
    this.store.dispatch(actions.toggleFlowExpansion({flowId}));
  }

  cancelFlow(clientId: string, flowId: string) {
    this.store.dispatch(actions.cancelFlow({clientId, flowId}));
  }

  startFlowConfiguration(name: string, initialArgs?: unknown) {
    this.store.dispatch(actions.startFlowConfiguration({name, initialArgs}));
  }

  stopFlowConfiguration() {
    this.store.dispatch(actions.stopFlowConfiguration());
  }

  queryFlowResults(query: FlowResultsQuery) {
    this.store.dispatch(actions.listFlowResults({query}));
  }

  readonly selectedFlowDescriptor$: Observable<FlowDescriptor|undefined> =
      this.store.select(selectors.flowInConfiguration)
          .pipe(
              withLatestFrom(this.configFacade.flowDescriptors$),
              map(([selectedFlow, fds]) => {
                if (selectedFlow === undefined) {
                  return undefined;
                }

                const fd = fds.get(selectedFlow.name);
                if (fd === undefined) {
                  throw new Error(
                      `Selected Flow ${selectedFlow.name} is not found.`);
                }

                return {
                  ...fd,
                  defaultArgs: selectedFlow.initialArgs ?? fd.defaultArgs,
                };
              }),
              // Generally, selectedFlow$ emits `undefined` as first value to
              // indicate that no flow has been selected. We use startWith() to
              // immediately emit this, even though flowDescriptors$ is still
              // waiting for the API result.
              startWith(undefined),
              shareReplay(1),
          );
}
