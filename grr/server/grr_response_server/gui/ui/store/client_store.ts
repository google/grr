import {computed, DestroyRef, effect, inject, untracked} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {tapResponse} from '@ngrx/operators';
import {
  getState,
  patchState,
  signalStore,
  withComputed,
  withHooks,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';
import {rxMethod} from '@ngrx/signals/rxjs-interop';
import {of, pipe, throwError} from 'rxjs';
import {startWith, switchMap, takeWhile} from 'rxjs/operators';

import {Any} from '../lib/api/api_interfaces';
import {
  DEFAULT_POLLING_INTERVAL,
  MissingApprovalError,
} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  Client,
  ClientApproval,
  ClientApprovalRequest,
  ClientSnapshot,
  StartupInfo,
} from '../lib/models/client';
import {
  Flow,
  FlowResult,
  FlowState,
  ListFlowResultsResult,
  ScheduledFlow,
} from '../lib/models/flow';
import {PayloadType} from '../lib/models/result';
import {compareDateNewestFirst} from '../lib/type_utils';
import {GlobalStore} from '../store/global_store';

/** Page size when loading flows. */
export const FLOWS_PAGE_SIZE = 50;

/** Query for fetching flow results. */
export interface FlowResultsQuery {
  readonly flowId: string | undefined;
  readonly offset: number;
  readonly count: number;
  readonly withTag: string;
  readonly withType: string;
}

/** Flow results grouped by payload type. */
export interface FlowResults {
  readonly flowResultsByPayloadType: Map<PayloadType, FlowResult[]>;
  readonly countLoaded: number;
  readonly totalCount: number;
}

/** A single entry in the client history. */
export interface ClientHistoryEntry {
  readonly snapshot?: ClientSnapshot;
  readonly startupInfo?: StartupInfo;
}

interface ClientStoreState {
  readonly clientId: string | null;
  readonly client: Client | null;
  readonly hasAccess: boolean | null;
  readonly clientApprovals: ClientApproval[];
  readonly clientSnapshots: ClientSnapshot[];
  readonly clientStartupInfos: StartupInfo[];
  // Flows
  // The number of flows that are currently loaded and displayed.
  readonly flowsCount: number;
  readonly flows: Flow[];
  // Flows that are accessed individually are fetched via the `pollFlow` method
  // and stored in this map. This also covers the case that an old flow is
  // loaded, that is not in the `flows` list. The downside is that one
  // additional api request is made for every accessed flow that was already
  // fetched via the `listFlowsForClient` method, however this is
  // should not be a performance issue as we have an index on the flow id
  // column.
  readonly flowsByFlowId: Map<string, Flow>;
  readonly flowResultsByFlowId: Map<string, FlowResults>;
  readonly scheduledFlows: ScheduledFlow[];

  // Increase when a refetch should be triggerd. The values themtselves are not
  // important, only the fact that they change will triggers an immediate fetch.
  readonly triggerFetchScheduledFlows: number;
  readonly triggerFetchFlows: number;
}

function getInitialState(): ClientStoreState {
  return {
    clientId: null, // Will be set by `initialize`
    client: null,
    hasAccess: null,
    clientApprovals: [],
    clientSnapshots: [],
    clientStartupInfos: [],
    flowsCount: FLOWS_PAGE_SIZE,
    flows: [],
    flowsByFlowId: new Map<string, Flow>(),
    flowResultsByFlowId: new Map<string, FlowResults>(),
    scheduledFlows: [],

    triggerFetchFlows: 0,
    triggerFetchScheduledFlows: 0,
  };
}
/**
 * Store for client data displayed on the client page.
 * - The lifecycle of this store is tied to the client page, this way the
 *   `client_id` is always known, and does not change.
 * - Data that is accessed by multiple subcomponents should be loaded once when
 *   the client page is accessed via the `initialize` function and any
 *   subcomponent can access the store to display the data.
 * - Additionally, rarely used data can be loaded on demand and stored using
 *   this store.
 */
// tslint:disable-next-line:enforce-name-casing
export const ClientStore = signalStore(
  withState<ClientStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    globalStore: inject(GlobalStore),
    destroyRef: inject(DestroyRef),
  })),
  withHooks({
    onInit({globalStore, ...store}) {
      // TODO: Ideally we would trigger the fetch of the scheduled
      // flows with an effect
      // (https://ngrx.io/guide/signals/signal-store/events) but they are still
      // experimantal and not available internally.
      effect(() => {
        getState(globalStore);
        // Use untracked to avoid triggering a change detection cycle.
        untracked(() => {
          patchState(store, {
            triggerFetchScheduledFlows: store.triggerFetchScheduledFlows() + 1,
          });
        });
      });
    },
  }),
  withMethods(({httpApiService, globalStore, destroyRef, ...store}) => ({
    initialize(clientId: string) {
      patchState(store, {clientId});

      this.pollClient();
      this.pollUntilAccess();
      this.fetchClientSnapshots();
      this.fetchClientStartupInfos();
    },
    pollClient(pollingInterval = DEFAULT_POLLING_INTERVAL) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      httpApiService
        .fetchClient(clientId, pollingInterval)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((client) => {
          patchState(store, {client});
        });
    },
    pollUntilAccess() {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      httpApiService
        .verifyClientAccess(clientId, DEFAULT_POLLING_INTERVAL)
        .pipe(
          takeUntilDestroyed(destroyRef),
          // We are only polling until access is granted, if a user loses
          // access during the session the state of `hasAccess` will not be
          // updated. This only has an effect on the UI state showing the
          // access, as API calls will still fail.
          takeWhile((hasAccess) => !hasAccess, true),
          startWith(null),
        )
        .subscribe((hasAccess) => {
          patchState(store, {
            hasAccess,
            // Start polling for flows as soon as we know access is granted.
            triggerFetchFlows: store.triggerFetchFlows() + 1,
          });
        });
    },
    pollClientApprovals(pollingInterval = DEFAULT_POLLING_INTERVAL) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      httpApiService
        .listClientApprovals(clientId, pollingInterval)
        .pipe(
          takeUntilDestroyed(destroyRef),
          takeWhile(
            (approvals: ClientApproval[]) =>
              !approvals?.find((approval) => approval.status.type === 'valid'),
            true,
          ),
        )
        .subscribe((approvals: ClientApproval[]) => {
          patchState(store, {clientApprovals: approvals});
        });
    },
    /**
     * Requests an approval for the current client and triggers an immediate
     * fetch of the approvals, to show the pending approval in the UI.
     */
    requestClientApproval(
      reason: string,
      approvers: string[],
      durationSeconds: number,
      ccEmail: string[],
    ) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      const requestArgs: ClientApprovalRequest = {
        clientId,
        reason,
        approvers,
        cc: ccEmail,
        expirationTimeUs: String(
          (new Date().getTime() + durationSeconds * 1000) * 1000,
        ),
      };
      httpApiService
        .requestClientApproval(requestArgs)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((approval) => {
          this.pollClientApprovals(0);
        });
    },
    /**
     *  Removes a client label and refetches the client to update its labels.
     */
    removeClientLabel(label: string) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      return httpApiService
        .removeClientLabel(clientId, label)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(() => {
          // The client is read-only, and might also have been updated
          // since the last time it was fetched, so we refetch it.
          httpApiService
            .fetchClient(clientId)
            .pipe(takeUntilDestroyed(destroyRef))
            .subscribe((client: Client) => {
              patchState(store, {client});
            });
        });
    },
    addClientLabel(label: string) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      return httpApiService
        .addClientLabel(clientId, label)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(() => {
          // The client is read-only, and might also have been updated
          // since the last time it was fetched, so we refetch it.
          httpApiService
            .fetchClient(clientId)
            .pipe(takeUntilDestroyed(destroyRef))
            .subscribe((client: Client) => {
              patchState(store, {client});
            });
        });
    },
    fetchClientSnapshots() {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      return httpApiService
        .fetchClientSnapshots(clientId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((snapshots) => {
          patchState(store, {clientSnapshots: snapshots.slice().reverse()});
        });
    },
    fetchClientStartupInfos() {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      return httpApiService
        .fetchClientStartupInfos(clientId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((startupInfos) => {
          patchState(store, {
            clientStartupInfos: startupInfos.slice().reverse(),
          });
        });
    },
    increaseFlowsCount(increaseBy: number) {
      patchState(store, {
        flowsCount: store.flowsCount() + increaseBy,
        triggerFetchFlows: store.triggerFetchFlows() + 1,
      });
    },
    pollFlows: rxMethod<number>(
      pipe(
        switchMap((triggerFetch: number) => {
          const clientId = store.clientId();
          if (clientId === null) {
            throw new Error('Client ID is not set. Call `initialize` first.');
          }
          if (!store.hasAccess()) {
            return of([]);
          }
          return httpApiService
            .listFlowsForClient(
              {
                clientId,
                count: store.flowsCount().toString(),
                topFlowsOnly: false,
              },
              DEFAULT_POLLING_INTERVAL,
            )
            .pipe(
              tapResponse({
                next: (flows: Flow[]) => {
                  flows.sort(compareDateNewestFirst((f: Flow) => f.startedAt));
                  patchState(store, {flows});
                },
                error: (err) => {
                  // TODO: Revisit this once approvals are
                  // implemented.
                  if (!(err instanceof MissingApprovalError)) {
                    throwError(() => err);
                  }
                },
              }),
            );
        }),
      ),
    ),
    pollScheduledFlows: rxMethod<number>(
      pipe(
        switchMap((triggerFetch: number) => {
          const clientId = store.clientId();
          if (clientId === null) {
            throw new Error('Client ID is not set. Call `initialize` first.');
          }
          const currentUser = globalStore.currentUser();
          if (currentUser === null) {
            // The `currentUser` is fetched asynchronously, so it's possible
            // that it's not available yet. In this case, we just abort here,
            // When the current user is available this method is called again.
            return of([]);
          }
          return httpApiService
            .listScheduledFlows(
              clientId,
              currentUser.name,
              DEFAULT_POLLING_INTERVAL,
            )
            .pipe(
              tapResponse({
                next: (scheduledFlows: ScheduledFlow[]) => {
                  scheduledFlows.sort(
                    compareDateNewestFirst((f: ScheduledFlow) => f.createTime),
                  );
                  patchState(store, {scheduledFlows});
                },
                error: (err) => {
                  // TODO: Revisit this once errors are handled.
                  throwError(() => err);
                },
              }),
            );
        }),
      ),
    ),
    scheduleOrStartFlow(
      flowName: string,
      flowArgs: unknown,
      disableRrgSupport: boolean,
    ) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      if (store.hasAccess()) {
        httpApiService
          .startFlow(clientId, flowName, flowArgs as Any, disableRrgSupport)
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((flow) => {
            // Updating the number of flows to fetch triggers an immediate
            // poll of the flows which updates the flow list, otherwise the
            // list would only be updated when the next poll is scheduled.
            // Increasing the number of flows by one, to make sure the same
            // flows plus the newly created one are fetched. (This is not
            // strictly needed and there could be another flow be created by
            // another user at the same time as well.)
            this.increaseFlowsCount(1);
          });
      } else {
        httpApiService
          .scheduleFlow(clientId, flowName, flowArgs as Any)
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((scheduledFlow) => {
            // Triggers an immediate poll of the scheduled flows, otherwise the
            // list would only be updated when the next poll is scheduled.
            patchState(store, {
              triggerFetchScheduledFlows:
                store.triggerFetchScheduledFlows() + 1,
            });
          });
      }
    },
    cancelFlow(flowId: string) {
      const clientId = store.clientId();
      if (clientId === null) {
        throw new Error('Client ID is not set. Call `initialize` first.');
      }
      httpApiService
        .cancelFlow(clientId, flowId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(() => {
          // Trigger an immediate poll of the flows, otherwise the
          // list would only be updated when the next poll is scheduled.
          patchState(store, {
            triggerFetchFlows: store.triggerFetchFlows() + 1,
          });
        });
    },
    pollFlow: rxMethod<string | undefined>(
      pipe(
        switchMap((flowId: string | undefined) => {
          const clientId = store.clientId();
          if (clientId === null) {
            throw new Error('Client ID is not set. Call `initialize` first.');
          }
          if (flowId === undefined) {
            // The flow id is read asynchronously from the URL, so it's possible
            // that it's not set yet. In this case, we just abort here, and wait
            // until the flow id is available.
            return of(null);
          }
          return httpApiService
            .pollFlow(clientId, flowId, DEFAULT_POLLING_INTERVAL)
            .pipe(
              tapResponse({
                next: (flow: Flow) => {
                  // Create a copy of the flowsByFlowId map because Angular's
                  // change detection relies on reference equality for signals.
                  const flowsByFlowId = new Map(store.flowsByFlowId());
                  flowsByFlowId.set(flowId, flow);
                  patchState(store, {flowsByFlowId});
                },
                error: (err) => {
                  // TODO: Revisit this once errors are handled.
                  throwError(() => err);
                },
              }),
            );
        }),
      ),
    ),
    pollFlowResults: rxMethod<FlowResultsQuery>(
      pipe(
        switchMap((query: FlowResultsQuery) => {
          const clientId = store.clientId();
          if (clientId === null) {
            throw new Error('Client ID is not set. Call `initialize` first.');
          }
          if (query.flowId == null) {
            // The flow id is read from the URL, so it's possible that it's not
            // set yet. In this case, we just abort here, and wait until the
            // flow id is available.
            return of([]);
          }
          if (query.count === 0) {
            return of([]);
          }
          const flowId = query.flowId;
          return httpApiService
            .listResultsForFlow(
              {
                clientId,
                flowId: query.flowId,
                count: query.count,
                offset: query.offset,
                withTag: query.withTag,
                withType: query.withType,
              },
              DEFAULT_POLLING_INTERVAL,
            )
            .pipe(
              tapResponse({
                next: (results: ListFlowResultsResult) => {
                  // Create a copy of the flowsByFlowId map because Angular's
                  // change detection relies on reference equality for signals.
                  const flowResultsByFlowId = new Map(
                    store.flowResultsByFlowId(),
                  );
                  const resultsMap = new Map<PayloadType, FlowResult[]>();
                  for (const res of results.results) {
                    if (res.payloadType) {
                      if (resultsMap.has(res.payloadType)) {
                        resultsMap.get(res.payloadType)!.push(res);
                      } else {
                        resultsMap.set(res.payloadType, [res]);
                      }
                    }
                  }
                  flowResultsByFlowId.set(flowId, {
                    flowResultsByPayloadType: resultsMap,
                    countLoaded: results.results.length,
                    totalCount: results.totalCount ?? 0,
                  });
                  patchState(store, {flowResultsByFlowId});
                },
                error: (err) => {
                  // TODO: Revisit this once errors are handled.
                  throwError(() => err);
                },
              }),
              takeWhile(() => {
                const flow = store.flowsByFlowId().get(flowId);
                if (flow == null) {
                  return true;
                }
                return (
                  flow?.state !== FlowState.FINISHED &&
                  flow?.state !== FlowState.ERROR
                );
              }),
            );
        }),
      ),
    ),
  })),
  withComputed((store) => ({
    clientHistory: computed<ClientHistoryEntry[]>(() => {
      const startupInfos = store.clientStartupInfos();
      const snapshots = store.clientSnapshots();

      // Intermediate type for items to be sorted
      type HistoryItem =
        | {type: 'startup'; timestamp: Date; data: StartupInfo}
        | {type: 'snapshot'; timestamp: Date; data: ClientSnapshot};

      // 1. Filter out entries without timestamps and transform to HistoryItem
      const validStartupInfos: HistoryItem[] = startupInfos
        .filter(
          (info): info is StartupInfo & {timestamp: Date} => !!info.timestamp,
        )
        .map((info) => ({
          type: 'startup',
          timestamp: info.timestamp,
          data: info,
        }));

      const validSnapshots: HistoryItem[] = snapshots
        .filter(
          (snap): snap is ClientSnapshot & {timestamp: Date} =>
            !!snap.timestamp,
        )
        .map((snap) => ({
          type: 'snapshot',
          timestamp: snap.timestamp,
          data: snap,
        }));

      const combinedItems: HistoryItem[] = [
        ...validStartupInfos,
        ...validSnapshots,
      ];

      // 3. Sort the combined array based on timestamp in reverse order.
      combinedItems.sort(
        (a, b) => b.timestamp.getTime() - a.timestamp.getTime(),
      );

      // 4. Map to the final ClientHistoryEntry[] structure
      const history: ClientHistoryEntry[] = combinedItems.map((item) => {
        if (item.type === 'startup') {
          return {startupInfo: item.data};
        } else {
          // item.type === 'snapshot'
          return {snapshot: item.data};
        }
      });

      return history;
    }),
    latestApproval: computed(
      () =>
        store
          .clientApprovals()
          ?.find((approval) => approval?.status.type !== 'expired') ?? null,
    ),
    // Ideally we would return the number of available flows when requesting the
    // list of flows, but the API does not support this. In case the client has
    // exactly as many flows as requested, we will not know if there are more
    // flows available. This is a best effort approximation.
    hasMoreFlows: computed(() => store.flowsCount() <= store.flows().length),
  })),
);
