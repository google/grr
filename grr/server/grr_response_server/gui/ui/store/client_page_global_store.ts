import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {ConfigService} from '@app/components/config/config';
import {AnyObject} from '@app/lib/api/api_interfaces';
import {HttpApiService, MissingApprovalError} from '@app/lib/api/http_api_service';
import {translateApproval, translateClient} from '@app/lib/api_translation/client';
import {translateFlow, translateScheduledFlow} from '@app/lib/api_translation/flow';
import {Flow, FlowDescriptor, ScheduledFlow} from '@app/lib/models/flow';
import {combineLatest, EMPTY, Observable, of, throwError, timer} from 'rxjs';
import {catchError, concatMap, distinctUntilChanged, exhaustMap, filter, map, mergeMap, shareReplay, skip, startWith, switchMap, switchMapTo, tap, withLatestFrom} from 'rxjs/operators';

import {translateApproverSuggestions} from '../lib/api_translation/user';
import {ApprovalRequest, Client, ClientApproval} from '../lib/models/client';
import {poll} from '../lib/polling';
import {isNonNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';


interface FlowInConfiguration {
  readonly name: string;
  readonly initialArgs?: unknown;
}

/** State of a flow being started. */
export type StartFlowState = {
  readonly state: 'request_not_sent'
}|{
  readonly state: 'request_sent',
}|{
  readonly state: 'started',
  readonly flow: Flow,
}|{
  readonly state: 'scheduled',
  readonly scheduledFlow: ScheduledFlow,
}|{
  readonly state: 'error',
  readonly error: string,
};

interface ClientPageState {
  readonly client?: Client;
  readonly clientId?: string;

  readonly lastRemovedClientLabel?: string;

  readonly approvals: {readonly [key: string]: ClientApproval};
  readonly approvalSequence: string[];
  readonly hasAccess?: boolean;

  readonly flowListEntries: {readonly [key: string]: Flow};
  readonly flowListEntrySequence: string[];

  readonly flowInConfiguration?: FlowInConfiguration;
  readonly startFlowState: StartFlowState;

  readonly approverSuggestions?: ReadonlyArray<string>;
}

/** ComponentStore implementation used by the GlobalStore. */
class ClientPageComponentStore extends ComponentStore<ClientPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
      private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    super({
      approvals: {},
      approvalSequence: [],
      flowListEntries: {},
      flowListEntrySequence: [],
      startFlowState: {state: 'request_not_sent'},
    });
  }

  /** Reducer updating the last removed client label. */
  private readonly updateLastRemovedClientLabel =
      this.updater<string>((state, lastRemovedClientLabel) => {
        return {
          ...state,
          lastRemovedClientLabel,
        };
      });

  /** Reducer updating the selected client. */
  private readonly updateSelectedClient =
      this.updater<Client>((state, client) => {
        return {
          ...state,
          client,
        };
      });

  /** Reducer resetting the store and setting the clientId. */
  readonly selectClient = this.updater<string>((state, clientId) => {
    // Clear complete state when new client is selected to prevent stale
    // information.
    return {
      clientId,
      approvals: {},
      approvalSequence: [],
      flowListEntries: {},
      flowListEntrySequence: [],
      startFlowState: {state: 'request_not_sent'},
    };
  });

  // Reducer updating the requested approval.
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

  private readonly updateHasAccess =
      this.updater<boolean>((state, hasAccess) => ({...state, hasAccess}));

  private updateFlowsFn(state: ClientPageState, flows: Flow[]) {
    const flowListEntries: {[key: string]: Flow} = Object.fromEntries([
      ...Object.entries(state.flowListEntries),
      ...flows.map(f => ([f.flowId, f])),
    ]);

    const flowListEntrySequence =
        Object.values(flowListEntries)
            .sort((a, b) => +b.startedAt - +a.startedAt)
            .map(f => f.flowId);

    return {
      ...state,
      flowListEntries,
      flowListEntrySequence,
    };
  }
  // Reducer updating flows.
  private readonly updateFlows = this.updater<Flow[]>(this.updateFlowsFn);

  // Reducer updating state after a flow is started.
  private readonly updateStartedFlow = this.updater<Flow>((state, flow) => {
    return {
      ...this.updateFlowsFn(state, [flow]),
      startFlowState: {state: 'started', flow},
      flowInConfiguration: undefined,
    };
  });

  // Reducer updating state after a flow has been scheduled.
  private readonly updateAfterScheduledFlow =
      this.updater<ScheduledFlow>((state, scheduledFlow) => {
        return {
          ...state,
          startFlowState: {state: 'scheduled', scheduledFlow},
          flowInConfiguration: undefined,
        };
      });

  // Updates the state after a flow scheduling fails with a given error.
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

  private readonly fetchClient = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.select(state => state.clientId)),
          filter(isNonNull),
          mergeMap(clientId => {
            return this.httpApiService.fetchClient(clientId);
          }),
          map(apiClient => translateClient(apiClient)),
          tap(client => {
            this.updateSelectedClient(client);
          }),
          ));

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> =
      poll({
        pollOn:
            timer(0, this.configService.config.selectedClientPollingIntervalMs),
        pollEffect: this.fetchClient,
        selector: this.select(state => state.client),
      })
          .pipe(
              filter(isNonNull),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  /** An observable emitting the client id of the selected client. */
  readonly selectedClientId$: Observable<string> =
      this.select(state => state.clientId).pipe(filter(isNonNull));

  /** An observable emitting the last removed client label. */
  readonly lastRemovedClientLabel$: Observable<string> =
      this.select(state => state.lastRemovedClientLabel)
          .pipe(
              filter(isNonNull),
          );

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
      this.select(state => state.flowInConfiguration).pipe(filter(isNonNull));

  private readonly listApprovals = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectedClientId$),
          switchMap(clientId => this.httpApiService.listApprovals(clientId)),
          map(apiApprovals => apiApprovals.map(translateApproval)),
          tap(approvals => {
            this.updateApprovals(approvals);
          })));

  private readonly latestApprovalValue$ = this.select(state => {
    // Approvals are expected to be in reversed chronological order.
    const foundId = state.approvalSequence.find(
        approvalId => state.approvals[approvalId].status.type !== 'expired');
    return foundId ? state.approvals[foundId] : undefined;
  });

  /** An observable emitting the latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval|undefined> =
      poll({
        pollOn: timer(0, this.configService.config.approvalPollingIntervalMs),
        pollEffect: this.listApprovals,
        selector: this.latestApprovalValue$,
        // Only poll when approval is missing or outdated. The user no longer
        // benefits from polling when they have a valid approval already.
        pollUntil: this.latestApprovalValue$.pipe(
            filter((approval) => approval?.status.type === 'valid')),
      }).pipe(shareReplay({bufferSize: 1, refCount: true}));

  private readonly verifyAccess = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectedClientId$),
          switchMap(
              clientId => this.httpApiService.verifyClientAccess(clientId)),
          tap(access => {
            this.updateHasAccess(access);
          })));

  readonly hasAccess$: Observable<boolean> =
      poll({
        pollOn: timer(0, this.configService.config.approvalPollingIntervalMs),
        pollEffect: this.verifyAccess,
        selector: this.select(state => state.hasAccess),
        // Only poll if hasAccess is undefined or false. In this case, changes
        // could happen any time soon.
        pollUntil: this.select(state => state.hasAccess)
                     .pipe(filter(hasAccess => !!hasAccess)),
      })
          .pipe(
              filter(isNonNull),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  readonly approvalsEnabled$: Observable<boolean> =
      combineLatest([this.hasAccess$, this.latestApproval$])
          .pipe(
              map(([hasAccess, latestApproval]) =>
                      !hasAccess || latestApproval !== undefined),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  private readonly flowListEntriesImpl$: Observable<ReadonlyArray<Flow>> =
      this.select(state => {
        return state.flowListEntrySequence.map(id => state.flowListEntries[id]);
      });

  private readonly listFlows = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.selectedClientId$),
          exhaustMap(
              clientId => this.httpApiService.listFlowsForClient(clientId).pipe(
                  catchError(err => {
                    if (err instanceof MissingApprovalError) {
                      return EMPTY;
                    } else {
                      return throwError(err);
                    }
                  }),
                  )),
          map(apiFlows => apiFlows.map(translateFlow)),
          tap(flows => {
            this.updateFlows(flows);
          }),
          ));

  /** An observable emitting current flow list entries. */
  readonly flowListEntries$: Observable<ReadonlyArray<Flow>> =
      poll({
        pollOn: timer(0, this.configService.config.flowListPollingIntervalMs),
        pollEffect: this.listFlows,
        selector: this.flowListEntriesImpl$,
      }).pipe(shareReplay({bufferSize: 1, refCount: true}));

  /** An observable emitting the start flow state. */
  readonly startFlowState$: Observable<StartFlowState> =
      this.select(state => state.startFlowState);

  /** An observable emitting the selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor|undefined> =
      this.select(state => state.flowInConfiguration)
          .pipe(
              withLatestFrom(this.configGlobalStore.flowDescriptors$),
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
              // Generally, selectedFlow$ emits `undefined` as first value
              // to indicate that no flow has been selected. We use
              // startWith() to immediately emit this, even though
              // flowDescriptors$ is still waiting for the API result.
              startWith(undefined),
              shareReplay({bufferSize: 1, refCount: true}),
          );

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

  /** Schedules a flow with given arguments. */
  readonly scheduleFlow = this.effect<unknown>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$, this.flowInConfiguration$),
          concatMap(([flowArgs, clientId, flowInConfiguration]) => {
            return this.httpApiService.scheduleFlow(
                clientId, flowInConfiguration.name, flowArgs as AnyObject);
          }),
          map(translateScheduledFlow),
          tap(flow => {
            this.updateAfterScheduledFlow(flow);
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

  private readonly updateApproverSuggestions =
      this.updater<ReadonlyArray<string>>((state, approverSuggestions) => {
        return {
          ...state,
          approverSuggestions,
        };
      });

  readonly suggestApprovers = this.effect<string>(
      obs$ => obs$.pipe(
          concatMap(
              (usernameQuery) =>
                  this.httpApiService.suggestApprovers(usernameQuery)),
          map(translateApproverSuggestions),
          tap((suggestions) => {
            this.updateApproverSuggestions(suggestions);
          }),
          ));

  readonly approverSuggestions$ =
      this.select((state) => state.approverSuggestions).pipe(filter(isNonNull));

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

  /** An effect to add a label to the selected client */
  readonly addClientLabel = this.effect<string>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$),
          switchMap(
              ([label, clientId]) =>
                  this.httpApiService.addClientLabel(clientId, label)),
          tap(() => {
            this.fetchClient();
          }),
          ));

  /** An effect to remove a label from the selected client */
  readonly removeClientLabel = this.effect<string>(
      obs$ => obs$.pipe(
          withLatestFrom(this.selectedClientId$),
          switchMap(
              ([label, clientId]) =>
                  this.httpApiService.removeClientLabel(clientId, label)),
          tap((label) => {
            this.fetchClient();
            this.updateLastRemovedClientLabel(label);
          }),
          ));
}

/** GlobalStore for client-related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientPageGlobalStore {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
      private readonly configGlobalStore: ConfigGlobalStore) {}

  private readonly store = new ClientPageComponentStore(
      this.httpApiService, this.configService, this.configGlobalStore);

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> = this.store.selectedClient$;

  /** An observable emitting latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval|undefined> =
      this.store.latestApproval$;

  /** An obserable emitting if the user has access to the client. */
  readonly hasAccess$ = this.store.hasAccess$;

  /**
   * An observable emitting if the approval system is enabled for the user.
   */
  readonly approvalsEnabled$ = this.store.approvalsEnabled$;

  /** An observable emitting current flow entries. */
  readonly flowListEntries$: Observable<ReadonlyArray<Flow>> =
      this.store.flowListEntries$;

  /** An observable emitting the state of a flow being started. */
  readonly startFlowState$: Observable<StartFlowState> =
      this.store.startFlowState$;

  /** An observable emitting currently selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor|undefined> =
      this.store.selectedFlowDescriptor$;

  /** An observable emitting the last removed client label. */
  readonly lastRemovedClientLabel$: Observable<string> =
      this.store.lastRemovedClientLabel$;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.selectClient(clientId);
  }

  /** Requests an approval for the currently selected client. */
  requestApproval(request: ApprovalRequest): void {
    this.store.requestApproval(request);
  }

  /** Starts a flow with given arguments. */
  startFlow(flowArgs: unknown) {
    this.store.startFlow(flowArgs);
  }

  /** Schedules a flow with given arguments. */
  scheduleFlow(flowArgs: unknown) {
    this.store.scheduleFlow(flowArgs);
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

  suggestApprovers(usernameQuery: string) {
    this.store.suggestApprovers(usernameQuery);
  }

  readonly approverSuggestions$ = this.store.approverSuggestions$;

  /** Adds a label to the selected client */
  addClientLabel(label: string) {
    this.store.addClientLabel(label);
  }

  /** Removes a label from the selected client */
  removeClientLabel(label: string) {
    this.store.removeClientLabel(label);
  }
}
