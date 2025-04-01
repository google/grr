import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, merge, Observable, of, throwError} from 'rxjs';
import {
  catchError,
  concatMap,
  distinctUntilChanged,
  filter,
  map,
  scan,
  shareReplay,
  skip,
  startWith,
  switchMap,
  take,
  takeWhile,
  tap,
  withLatestFrom,
} from 'rxjs/operators';

import {Any} from '../lib/api/api_interfaces';
import {
  HttpApiService,
  MissingApprovalError,
} from '../lib/api/http_api_service';
import {
  extractErrorMessage,
  RequestStatus,
  RequestStatusType,
  trackRequest,
} from '../lib/api/track_request';
import {
  translateClient,
  translateClientApproval,
} from '../lib/api_translation/client';
import {
  translateFlow,
  translateScheduledFlow,
} from '../lib/api_translation/flow';
import {
  Client,
  ClientApproval,
  ClientApprovalRequest,
} from '../lib/models/client';
import {Flow, FlowDescriptor, ScheduledFlow} from '../lib/models/flow';
import {assertNonNull, isNonNull, isNull} from '../lib/preconditions';
import {compareDateNewestFirst} from '../lib/type_utils';

import {ConfigGlobalStore} from './config_global_store';

interface FlowInConfiguration {
  readonly name: string;
  readonly initialArgs?: unknown;
}

/** State of a flow being started. */
export type StartFlowState =
  | {
      readonly flow: Flow;
    }
  | {
      readonly scheduledFlow: ScheduledFlow;
    };

interface ClientPageState {
  readonly clientId?: string;

  readonly lastRemovedClientLabel?: string;

  readonly flowInConfiguration?: FlowInConfiguration;
  readonly startFlowState?: RequestStatus<StartFlowState, string>;

  readonly listFlowsCount: number;

  readonly requestApprovalStatus?: RequestStatus<ClientApproval, string>;
}

/** Page size when loading older flows. */
export const FLOWS_PAGE_SIZE = 20;

/** The state of loading flow list entries. */
export interface FlowListState {
  /**
   * True, whenever new flows are being loaded, e.g. upon page load and when
   * more flows are being loaded. This stays false during the re-polling of
   * already loaded flows.
   */
  isLoading: boolean;
  flows?: Flow[];
  hasMore?: boolean;
}

/** ComponentStore implementation used by the GlobalStore. */
class ClientPageComponentStore extends ComponentStore<ClientPageState> {
  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    super({
      listFlowsCount: 0,
    });
    this.selectedFlowDescriptor$ = this.select(
      (state) => state.flowInConfiguration,
    ).pipe(
      withLatestFrom(this.configGlobalStore.flowDescriptors$),
      map(([selectedFlow, fds]) => {
        if (selectedFlow === undefined) {
          return null;
        }

        const fd = fds.get(selectedFlow.name);
        if (fd === undefined) {
          throw new Error(`Selected Flow ${selectedFlow.name} is not found.`);
        }

        return {
          ...fd,
          defaultArgs: selectedFlow.initialArgs ?? fd.defaultArgs,
        };
      }),
      startWith(null),
      shareReplay({bufferSize: 1, refCount: true}),
    );
    this.requestClientApproval = this.effect<ClientApprovalRequest>((obs$) =>
      obs$.pipe(
        switchMap((approvalRequest) =>
          trackRequest(
            this.httpApiService
              .requestClientApproval(approvalRequest)
              .pipe(map(translateClientApproval)),
          ),
        ),
        map(extractErrorMessage),
        tap((requestApprovalStatus) => {
          this.patchState({requestApprovalStatus});
        }),
      ),
    );
    this.startFlow = this.effect<unknown>((obs$) =>
      obs$.pipe(
        withLatestFrom(this.selectedClientId$, this.flowInConfiguration$),
        concatMap(([flowArgs, clientId, flowInConfiguration]) => {
          assertNonNull(clientId, 'clientId');
          return trackRequest(
            this.httpApiService
              .startFlow(clientId, flowInConfiguration.name, flowArgs as Any)
              .pipe(map((flow) => ({flow: translateFlow(flow)}))),
          );
        }),
        tap((requestStatus) => {
          this.updateFlowFormRequestStatus(requestStatus);
        }),
      ),
    );
    this.scheduleFlow = this.effect<unknown>((obs$) =>
      obs$.pipe(
        withLatestFrom(this.selectedClientId$, this.flowInConfiguration$),
        concatMap(([flowArgs, clientId, flowInConfiguration]) => {
          assertNonNull(clientId, 'clientId');
          return trackRequest(
            this.httpApiService
              .scheduleFlow(clientId, flowInConfiguration.name, flowArgs as Any)
              .pipe(map((sf) => ({scheduledFlow: translateScheduledFlow(sf)}))),
          );
        }),
        tap((requestStatus) => {
          this.updateFlowFormRequestStatus(requestStatus);
        }),
      ),
    );
    this.scheduleOrStartFlow = this.effect<unknown>((obs$) =>
      obs$.pipe(
        switchMap((flowArgs) =>
          this.hasAccess$.pipe(
            filter(isNonNull),
            take(1),
            tap((hasAccess) => {
              if (hasAccess) {
                this.startFlow(flowArgs);
              } else {
                this.scheduleFlow(flowArgs);
              }
            }),
          ),
        ),
      ),
    );
    this.cancelFlow = this.effect<string>((obs$) =>
      obs$.pipe(
        withLatestFrom(this.selectedClientId$),
        concatMap(([flowId, clientId]) => {
          assertNonNull(clientId, 'clientId');
          return trackRequest(this.httpApiService.cancelFlow(clientId, flowId));
        }),
      ),
    );
    this.startFlowConfigurationImpl = this.updater<[string, unknown]>(
      (state, [name, initialArgs]) => {
        return {
          ...state,
          flowInConfiguration: {name, initialArgs},
          startFlowState: undefined,
        };
      },
    );
    this.stopFlowConfiguration = this.updater<void>((state) => {
      return {
        ...state,
        flowInConfiguration: undefined,
        startFlowState: undefined,
      };
    });
    this.addClientLabel = this.effect<string>((obs$) =>
      obs$.pipe(
        withLatestFrom(this.selectedClientId$),
        switchMap(([label, clientId]) => {
          assertNonNull(clientId, 'clientId');
          return trackRequest(
            this.httpApiService.addClientLabel(clientId, label),
          );
        }),
      ),
    );
    this.removeClientLabel = this.effect<string>((obs$) =>
      obs$.pipe(
        withLatestFrom(this.selectedClientId$),
        switchMap(([label, clientId]) => {
          assertNonNull(clientId, 'clientId');
          return trackRequest(
            this.httpApiService.removeClientLabel(clientId, label),
          );
        }),
        tap((status) => {
          if (status.status === RequestStatusType.SUCCESS) {
            this.updateLastRemovedClientLabel(status.data);
          }
        }),
      ),
    );
  }

  /** Reducer updating the last removed client label. */
  private readonly updateLastRemovedClientLabel = this.updater<string>(
    (state, lastRemovedClientLabel) => {
      return {
        ...state,
        lastRemovedClientLabel,
      };
    },
  );

  /** Reducer resetting the store and setting the clientId. */
  readonly selectClient = this.updater<string>((state, clientId) => {
    if (state.clientId === clientId) {
      return state;
    }

    // Clear complete state when new client is selected to prevent stale
    // information.
    return {
      clientId,
      flowListEntries: {},
      flowListEntrySequence: [],
      listFlowsCount: FLOWS_PAGE_SIZE,
    };
  });

  private readonly updateFlowFormRequestStatus = this.updater<
    RequestStatus<StartFlowState>
  >((state, startFlowState) => ({
    ...state,
    startFlowState: extractErrorMessage(startFlowState),
    flowInConfiguration:
      startFlowState.status === RequestStatusType.SUCCESS
        ? undefined
        : state.flowInConfiguration,
  }));

  /** An observable emitting the client id of the selected client. */
  readonly selectedClientId$: Observable<string | null> = this.select(
    (state) => state.clientId ?? null,
  ).pipe(distinctUntilChanged());

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client | null> =
    this.selectedClientId$.pipe(
      switchMap((clientId) =>
        clientId
          ? this.httpApiService
              .subscribeToClient(clientId)
              .pipe(map(translateClient), startWith(null))
          : of(null),
      ),
      shareReplay({bufferSize: 1, refCount: true}),
    );

  /** An observable emitting the last removed client label. */
  readonly lastRemovedClientLabel$: Observable<string | null> = this.select(
    (state) => state.lastRemovedClientLabel ?? null,
  );

  /**
   * An observable that is triggered when selected client id changes.
   * Won't emit anything on subscription.
   */
  readonly selectedClientIdChanged$ = this.selectedClientId$.pipe(
    filter(isNonNull),
    distinctUntilChanged(),
    // selectedClientId$ will always replay the latest value.
    // Consequently - we need to skip it.
    skip(1),
  );

  /** An observable emitting current flow configuration. */
  readonly flowInConfiguration$: Observable<FlowInConfiguration> = this.select(
    (state) => state.flowInConfiguration,
  ).pipe(filter(isNonNull));

  private readonly approvals$ = this.selectedClientId$.pipe(
    switchMap((clientId) => {
      if (!clientId) {
        return of(null);
      }

      return this.httpApiService.subscribeToListClientApprovals(clientId).pipe(
        map((approvals) => approvals?.map(translateClientApproval)),
        takeWhile(
          (approvals) =>
            !approvals?.find((approval) => approval.status.type === 'valid'),
          true,
        ),
        startWith(null),
      );
    }),
  );

  /** An observable emitting the latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval | null> =
    this.approvals$.pipe(
      // Approvals are expected to be in reversed chronological order.
      map(
        (approvals) =>
          approvals?.find((approval) => approval?.status.type !== 'expired') ??
          null,
      ),
      shareReplay({bufferSize: 1, refCount: true}),
    );

  readonly clientApprovalRoute$: Observable<string[]> =
    this.latestApproval$.pipe(
      filter(isNonNull),
      map((latestApproval: ClientApproval): string[] => {
        return [
          'clients',
          latestApproval.clientId,
          'users',
          latestApproval.requestor,
          'approvals',
          latestApproval.approvalId,
        ];
      }),
      startWith([]),
    );

  readonly hasAccess$: Observable<boolean | null> = this.selectedClientId$.pipe(
    switchMap((clientId) =>
      clientId
        ? this.httpApiService.subscribeToVerifyClientAccess(clientId).pipe(
            takeWhile((hasAccess) => !hasAccess, true),
            startWith(null),
          )
        : of(null),
    ),
    shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly approvalsEnabled$: Observable<boolean | null> = combineLatest([
    this.hasAccess$,
    this.latestApproval$,
  ]).pipe(
    map(([hasAccess, latestApproval]) =>
      isNull(hasAccess) ? null : !hasAccess || isNonNull(latestApproval),
    ),
    shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly listFlowsCount$ = this.select((state) => state.listFlowsCount);

  readonly loadMoreFlows = this.updater<void>((state) => ({
    ...state,
    listFlowsCount: state.listFlowsCount + FLOWS_PAGE_SIZE,
  }));

  private subscribeToFlowsForClient(
    clientId: string,
  ): Observable<FlowListState> {
    return this.listFlowsCount$.pipe(
      switchMap<number, Observable<FlowListState>>((count) =>
        merge(
          // Whenever more flows are requested, listFlowsCount changes and
          // we emit `isLoading: true` immediately.
          of<FlowListState>({isLoading: true} as FlowListState),
          this.httpApiService
            .subscribeToFlowsForClient({
              clientId,
              count: count.toString(),
              topFlowsOnly: true,
            })
            .pipe(
              map((apiFlows) =>
                apiFlows
                  .map(translateFlow)
                  .sort(compareDateNewestFirst((f) => f.startedAt)),
              ),
              map(
                (flows) =>
                  ({
                    flows,
                    isLoading: false,
                    hasMore: flows.length >= count,
                  }) as FlowListState,
              ),
              catchError<FlowListState, Observable<FlowListState>>((err) =>
                err instanceof MissingApprovalError
                  ? of({isLoading: false} as FlowListState)
                  : throwError(err),
              ),
            ),
        ),
      ),
      // Re-emit old flows while new flows are being loaded to prevent the UI
      // from showing a blank state after triggering loading of more flows.
      scan<FlowListState, FlowListState>(
        (acc, next) => ({...next, flows: next.flows ?? acc.flows}),
        {isLoading: false} as FlowListState,
      ),
    );
  }

  /** An observable emitting current flow list entries sorted by start time. */
  readonly flowListEntries$: Observable<FlowListState> = combineLatest([
    this.selectedClientId$,
    this.hasAccess$,
  ]).pipe(
    switchMap(([clientId, hasAccess]) =>
      clientId && hasAccess
        ? this.subscribeToFlowsForClient(clientId)
        : of({isLoading: false}),
    ),
    shareReplay({bufferSize: 1, refCount: true}),
  );

  /** An observable emitting the start flow state. */
  readonly startFlowStatus$: Observable<RequestStatus<
    StartFlowState,
    string
  > | null> = this.select((state) => state.startFlowState ?? null);

  readonly requestApprovalStatus$: Observable<RequestStatus<
    ClientApproval,
    string
  > | null> = this.select((state) => state.requestApprovalStatus ?? null);

  /** An observable emitting the selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor | null>;

  /** An effect requesting a new client approval. */
  readonly requestClientApproval;

  /** Starts a flow with given arguments. */
  readonly startFlow;

  /** Schedules a flow with given arguments. */
  readonly scheduleFlow;

  readonly scheduleOrStartFlow;

  /** Cancels given flow. */
  readonly cancelFlow;

  private readonly startFlowConfigurationImpl;

  /** Starts the process of flow configuration in the UI. */
  startFlowConfiguration(name: string, initialArgs?: unknown) {
    this.startFlowConfigurationImpl([name, initialArgs]);
  }

  /** Stops the process of flow configuration in the UI. */
  readonly stopFlowConfiguration;

  /** An effect to add a label to the selected client */
  readonly addClientLabel;

  /** An effect to remove a label from the selected client */
  readonly removeClientLabel;
}

/** GlobalStore for client-related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientPageGlobalStore {
  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    this.store = new ClientPageComponentStore(
      this.httpApiService,
      this.configGlobalStore,
    );
    this.selectedClient$ = this.store.selectedClient$;
    this.latestApproval$ = this.store.latestApproval$;
    this.clientApprovalRoute$ = this.store.clientApprovalRoute$;
    this.hasAccess$ = this.store.hasAccess$;
    this.approvalsEnabled$ = this.store.approvalsEnabled$;
    this.flowListEntries$ = this.store.flowListEntries$;
    this.startFlowStatus$ = this.store.startFlowStatus$;
    this.requestApprovalStatus$ = this.store.requestApprovalStatus$;
    this.selectedFlowDescriptor$ = this.store.selectedFlowDescriptor$;
    this.lastRemovedClientLabel$ = this.store.lastRemovedClientLabel$;
  }

  private readonly store;

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client | null>;

  /** An observable emitting latest non-expired approval. */
  readonly latestApproval$: Observable<ClientApproval | null>;

  /** An observable emitting latest approval route. */
  readonly clientApprovalRoute$: Observable<string[]>;

  /** An obserable emitting if the user has access to the client. */
  readonly hasAccess$;

  /**
   * An observable emitting if the approval system is enabled for the user.
   */
  readonly approvalsEnabled$;

  /** An observable emitting current flow entries. */
  readonly flowListEntries$: Observable<FlowListState>;

  /** An observable emitting the state of a flow being started. */
  readonly startFlowStatus$: Observable<RequestStatus<
    StartFlowState,
    string
  > | null>;

  readonly requestApprovalStatus$: Observable<RequestStatus<
    ClientApproval,
    string
  > | null>;

  /** An observable emitting currently selected flow descriptor. */
  readonly selectedFlowDescriptor$: Observable<FlowDescriptor | null>;

  /** An observable emitting the last removed client label. */
  readonly lastRemovedClientLabel$: Observable<string | null>;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.selectClient(clientId);
  }

  /** Requests an approval for the currently selected client. */
  requestClientApproval(request: ClientApprovalRequest): void {
    this.store.requestClientApproval(request);
  }

  /** Starts a flow with given arguments. */
  startFlow(flowArgs: unknown) {
    this.store.startFlow(flowArgs);
  }

  /** Schedules a flow with given arguments. */
  scheduleFlow(flowArgs: unknown) {
    this.store.scheduleFlow(flowArgs);
  }

  scheduleOrStartFlow(flowArgs: unknown) {
    this.store.scheduleOrStartFlow(flowArgs);
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

  /** Adds a label to the selected client */
  addClientLabel(label: string) {
    this.store.addClientLabel(label);
  }

  /** Removes a label from the selected client */
  removeClientLabel(label: string) {
    this.store.removeClientLabel(label);
  }

  loadMoreFlows() {
    this.store.loadMoreFlows();
  }
}
