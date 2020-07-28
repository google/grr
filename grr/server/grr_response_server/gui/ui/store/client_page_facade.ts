import {Injectable} from '@angular/core';
import {ConfigService} from '@app/components/config/config';
import {AnyObject} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateApproval, translateClient} from '@app/lib/api_translation/client';
import {translateFlow, translateFlowResult} from '@app/lib/api_translation/flow';
import {Flow, FlowDescriptor, FlowListEntry, flowListEntryFromFlow, FlowResultSet, FlowResultSetState, FlowResultsQuery, FlowState, updateFlowListEntryResultSet} from '@app/lib/models/flow';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, interval, merge, Observable, of, Subject, timer} from 'rxjs';
import {catchError, concatMap, distinctUntilChanged, exhaustMap, filter, map, mergeAll, mergeMap, shareReplay, skip, startWith, switchMap, switchMapTo, takeUntil, takeWhile, tap, withLatestFrom} from 'rxjs/operators';

import {ApprovalRequest, Client, ClientApproval} from '../lib/models/client';

import {ConfigFacade} from './config_facade';


interface FlowInConfiguration {
  readonly name: string;
  readonly initialArgs?: unknown;
}

/** State of a flow being started. */
export type StartFlowState = {
  readonly state: 'request_not_sent'
} | {
  readonly state: 'request_sent',
} | {
  readonly state: 'success',
  readonly flow: Flow,
} | {
  readonly state: 'error',
  readonly error: string,
};

interface ClientPageState {
  readonly client?: Client;
  readonly clientId?: string;

  readonly approvals: {readonly [key: string]: ClientApproval};
  readonly approvalSequence: string[];

  readonly flowListEntries: {readonly [key: string]: FlowListEntry};
  readonly flowListEntrySequence: string[];

  readonly flowInConfiguration?: FlowInConfiguration;
  readonly startFlowState: StartFlowState;
}

/**
 * ComponentStore implementation used by the ClientPageFacade. Shouldn't be
 * used directly. Declared as an exported global symbol to make dependency
 * injection possible.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientPageStore extends ComponentStore<ClientPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
      private readonly configFacade: ConfigFacade,
  ) {
    super({
      approvals: {},
      approvalSequence: [],
      flowListEntries: {},
      flowListEntrySequence: [],
      startFlowState: {state: 'request_not_sent'},
    });
  }

  /** Reducer updating the selected client. */
  private readonly updateSelectedClient =
      this.updater<Client>((state, client) => {
        return {
          ...state,
          client,
        };
      });

  /** Reducer updating the clientId in the store's state. */
  readonly selectClient = this.updater<string>((state, clientId) => {
    return {
      ...state,
      clientId,
    };
  });

  /** Reducer updating the requested approval. */
  private readonly updateApprovals =
      this.updater<ClientApproval[]>((state, approvals) => {
        const approvalsMap: {[key: string]: ClientApproval} = {};
        for (const approval of approvals) {
          approvalsMap[approval.approvalId] = approval;
        }

        return {
          ...state,
          approvals: approvalsMap,
          approvalSequence: approvals.map(a => a.approvalId),
        };
      });

  private updateFlowsFn(state: ClientPageState, flows: Flow[]) {
    const flowsToUpdate: FlowListEntry[] = flows.map((f) => {
      const existing = state.flowListEntries[f.flowId];
      if (existing) {
        return {...existing, flow: f};
      } else {
        return flowListEntryFromFlow(f);
      }
    });
    const newFlowListEntries = {...state.flowListEntries};
    for (const f of flowsToUpdate) {
      newFlowListEntries[f.flow.flowId] = f;
    }

    const sortedFlows = [...flows];
    sortedFlows.sort((a, b) => b.startedAt.valueOf() - a.startedAt.valueOf());

    return {
      ...state,
      flowListEntries: newFlowListEntries,
      flowListEntrySequence: sortedFlows.map(f => f.flowId),
    };
  }
  /** Reducer updating flows. */
  private readonly updateFlows = this.updater<Flow[]>(this.updateFlowsFn);

  /** Reducer updating flow results. */
  private readonly updateFlowResults =
      this.updater<FlowResultSet>((state, resultSet) => {
        const fle = state.flowListEntries[resultSet.sourceQuery.flowId];
        if (!fle) {
          // Assuming that there's no such flow in the list anymore.
          return state;
        }

        return {
          ...state,
          flowListEntries: {
            ...state.flowListEntries,
            [fle.flow.flowId]: updateFlowListEntryResultSet(fle, resultSet),
          },
        };
      });

  /** Reducer updating state after a flow is started. */
  private readonly updateStartedFlow = this.updater<Flow>((state, flow) => {
    return {
      ...this.updateFlowsFn(state, [flow]),
      startFlowState: {state: 'success', flow},
      flowInConfiguration: undefined,
    };
  });

  /** Updates the state after a flow scheduling fails with a given error. */
  private readonly updateStartFlowFailure =
      this.updater<string>((state, error) => {
        return {
          ...state,
          startFlowState: {
            state: 'error',
            error,
          },
        };
      });

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> =
      combineLatest(
          timer(0, this.configService.config.selectedClientPollingIntervalMs)
              .pipe(tap(() => this.fetchClient())),
          this.select(state => state.client))
          .pipe(
              map(([i, client]) => client),
              filter((client): client is Client => client !== undefined),
          );

  /** An observable emitting the client id of the selected client. */
  readonly selectedClientId$: Observable<string> =
      this.select(state => state.clientId)
          .pipe(
              filter((clientId): clientId is string => clientId !== undefined));

  /**
   * An observable that is triggered when selected client id changes.
   * Won't emit anything on subscription.
   */
  readonly selectedClientIdChanged$ = this.selectedClientId$.pipe(
      distinctUntilChanged(),
      // selectedClientId$ will always replay the latest value.
      // Consequently - we need to skip it.
      skip(1),
  );

  /** An observable emitting current flow configuration. */
  readonly flowInConfiguration$: Observable<FlowInConfiguration> =
      this.select(state => state.flowInConfiguration)
          .pipe(
              filter((fic): fic is FlowInConfiguration => fic !== undefined),
          );

  /** An observable emitting the latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval|undefined> =
      of(undefined).pipe(
          tap(() => this.listApprovals()), switchMapTo(this.select(state => {
            // Approvals are expected to be in reversed chronological order.
            const foundId = state.approvalSequence.find(
                approvalId =>
                    state.approvals[approvalId].status.type !== 'expired');
            return foundId ? state.approvals[foundId] : undefined;
          })));

  private readonly flowListEntriesImpl$:
      Observable<ReadonlyArray<FlowListEntry>> = this.select(state => {
        return state.flowListEntrySequence.map(id => state.flowListEntries[id]);
      });

  /** An observable emitting current flow list entries. */
  readonly flowListEntries$: Observable<ReadonlyArray<FlowListEntry>> =
      combineLatest([
        timer(0, this.configService.config.flowListPollingIntervalMs)
            .pipe(tap(() => {
              this.listFlows();
            })),
        this.flowListEntriesImpl$
      ])
          .pipe(
              map(([i, entries]) => entries),
              distinctUntilChanged(),
          );

  /** An observable emitting the start flow state. */
  readonly startFlowState$: Observable<StartFlowState> =
      this.select(state => state.startFlowState);

  /** An observable emitting the selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor|undefined> =
      this.select(state => state.flowInConfiguration)
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

  /** An effect fetching a client with a given id and updating the state. */
  private readonly fetchClient = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.select(state => state.clientId)),
          filter((clientId): clientId is string => clientId !== undefined),
          mergeMap(clientId => {
            return this.httpApiService.fetchClient(clientId);
          }),
          map(apiClient => translateClient(apiClient)),
          tap(client => {
            this.updateSelectedClient(client);
          }),
          ));


  /** An effect querying results of a given flow. */
  private readonly queryFlowResultsImpl = this.effect<FlowResultsQuery>(
      obs$ => obs$.pipe(
          takeUntil(this.selectedClientIdChanged$),
          withLatestFrom(this.selectedClientId$),
          exhaustMap(([query, clientId]) => {
            return combineLatest([
              of(query),
              this.httpApiService.listResultsForFlow(clientId, query),
            ]);
          }),
          map(([query, flowResults]) => {
            return {
              sourceQuery: query,
              state: FlowResultSetState.FETCHED,
              items: flowResults.map(translateFlowResult),
            } as FlowResultSet;
          }),
          tap((flowResultSet) => {
            this.updateFlowResults(flowResultSet);
          }),
          ));

  /**
   * Triggers flow results query. Results will be automatically updated until
   * the flow completes or another client is selected.
   */
  queryFlowResults(query: FlowResultsQuery) {
    const fleSelector =
        this.select((state) => state.flowListEntries[query.flowId]);

    return combineLatest([
             timer(0, this.configService.config.flowResultsPollingIntervalMs),
             fleSelector,
           ])
        .pipe(
            takeUntil(this.selectedClientIdChanged$),
            takeWhile(([i, fle]) => fle !== undefined),
            // Inclusive: the line below will trigger one more time, once
            // the flow state becomes FINISHED. This guarantees that results
            // will be updated correctly.
            takeWhile(
                ([i, fle]) => fle.flow.state !== FlowState.FINISHED, true),
            map(([i, fle]) => i),
            distinctUntilChanged(),
            tap(() => {
              this.queryFlowResultsImpl(query);
            }),
            )
        .subscribe();
  }

  /** An effect requesting a new client approval. */
  readonly requestApproval = this.effect<ApprovalRequest>(
      obs$ => obs$.pipe(
          switchMap(approvalRequest => {
            return this.httpApiService.requestApproval(approvalRequest);
          }),
          map(apiApproval => translateApproval(apiApproval)),
          tap(approval => {
            this.updateApprovals([approval]);
          }),
          ));

  /** Starts a flow with given arguments. */
  readonly startFlow = this.effect<unknown>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$, this.flowInConfiguration$),
          concatMap(([flowArgs, clientId, flowInConfiguration]) => {
            return this.httpApiService.startFlow(
                clientId, flowInConfiguration.name, flowArgs as AnyObject);
          }),
          map(translateFlow),
          tap(flow => {
            this.updateStartedFlow(flow);
          }),
          catchError((error: Error) => {
            this.updateStartFlowFailure(error.message);
            return of(undefined);
          }),
          ));

  /** Cancels given flow. */
  readonly cancelFlow = this.effect<string>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$),
          concatMap(([flowId, clientId]) => {
            return this.httpApiService.cancelFlow(clientId, flowId);
          }),
          map(translateFlow),
          tap((flow) => {
            this.updateFlows([flow]);
          }),
          ));

  private readonly startFlowConfigurationImpl =
      this.updater<[string, unknown]>((state, [name, initialArgs]) => {
        return {
          ...state,
          flowInConfiguration: {name, initialArgs},
          startFlowState: {state: 'request_not_sent'},
        };
      });

  /** Starts the process of flow configuration in the UI. */
  startFlowConfiguration(name: string, initialArgs?: unknown) {
    this.startFlowConfigurationImpl([name, initialArgs]);
  }

  /** Stops the process of flow configuration in the UI. */
  readonly stopFlowConfiguration = this.updater<void>((state) => {
    return {
      ...state,
      flowInConfiguration: undefined,
      startFlowState: {state: 'request_not_sent'},
    };
  });

  /** An effect to list approvals. */
  private readonly listApprovals = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectedClientId$),
          switchMap(clientId => this.httpApiService.listApprovals(clientId)),
          map(apiApprovals => apiApprovals.map(translateApproval)),
          tap(approvals => {
            this.updateApprovals(approvals);
          })));

  /** An effect to list flows. */
  private readonly listFlows = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectedClientId$),
          exhaustMap(
              clientId => this.httpApiService.listFlowsForClient(clientId)),
          map(apiFlows => apiFlows.map(translateFlow)),
          tap(flows => {
            this.updateFlows(flows);
          }),
          ));

  // An effect to add a label to the selected client
  readonly addClientLabel = this.effect<string>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$),
          switchMap(
              ([label, clientId]) =>
                  this.httpApiService.addClientLabel(clientId, label)),
          tap(() => this.fetchClient()),
          ));
}

/** Facade for client-related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientPageFacade {
  constructor(private readonly store: ClientPageStore) {}

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> = this.store.selectedClient$;

  /** An observable emitting latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval|undefined> =
      this.store.latestApproval$;

  /** An observable emitting current flow entries. */
  readonly flowListEntries$: Observable<ReadonlyArray<FlowListEntry>> =
      this.store.flowListEntries$;

  /** An observable emitting the state of a flow being started. */
  readonly startFlowState$: Observable<StartFlowState> =
      this.store.startFlowState$;

  /** An observable emitting currently selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor|undefined> =
      this.store.selectedFlowDescriptor$;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.selectClient(clientId);
  }

  /** Requests an approval for the currently selected client. */
  requestApproval(request: ApprovalRequest): void {
    this.store.requestApproval(request);
  }

  /** Queries results for a given flow. */
  queryFlowResults(query: FlowResultsQuery) {
    this.store.queryFlowResults(query);
  }

  /** Starts a flow with given arguments. */
  startFlow(flowArgs: unknown) {
    this.store.startFlow(flowArgs);
  }

  /** Cancels given flow. */
  cancelFlow(flowId: string) {
    this.store.cancelFlow(flowId);
  }

  /** Starts the process of configuring the flow to be launched. */
  startFlowConfiguration(name: string, initialArgs?: unknown) {
    this.store.startFlowConfiguration(name, initialArgs);
  }

  /** Stops the flow configuration process. */
  stopFlowConfiguration() {
    this.store.stopFlowConfiguration();
  }

  addClientLabel(label: string) {
    this.store.addClientLabel(label);
  }
}
