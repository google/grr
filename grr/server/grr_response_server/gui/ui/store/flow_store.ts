import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {
  patchState,
  signalStore,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  Flow,
  FlowLog,
  FlowLogs,
  FlowResult,
  ListAllOutputPluginLogsResult,
  ListFlowResultsResult,
  OutputPluginLogEntry,
} from '../lib/models/flow';
import {PayloadType} from '../lib/models/result';

const DEFAULT_COUNT_FLOW_RESULTS = 500;

interface FlowStoreState {
  readonly clientId: string | undefined;
  readonly flowId: string | undefined;

  flow: Flow | undefined;
  flowResultsByPayloadType: Map<PayloadType, FlowResult[]>;
  countLoadedResults: number;
  countTotalResults: number | undefined;
  readonly logs: readonly FlowLog[];
  readonly outputPluginLogs: readonly OutputPluginLogEntry[];
}

const initialState: FlowStoreState = {
  clientId: undefined, // Will be set by `initialize`
  flowId: undefined, // Will be set by `initialize`

  flow: undefined,
  flowResultsByPayloadType: new Map<PayloadType, FlowResult[]>(),
  countLoadedResults: 0,
  countTotalResults: undefined,
  logs: [],
  outputPluginLogs: [],
};

/**
 * Store for flow specific data.
 * - The lifecycle of this store is tied to the flow details page / fleet
 *   collection client results component, this way the `client_id` and `flow_id`
 *   are always known, and do not change.
 * - Data that is accessed by multiple subcomponents should be loaded once when
 *   the flow details page is accessed via the `initialize` function and any
 *   subcomponent can access the store to display the data.
 * - Flow data that is expected to be accessed across multiple flows, e.g. flow
 *   results, should be stored on the client store to keep it cached when
 *   navigating between flows.
 */
// tslint:disable-next-line:enforce-name-casing
export const FlowStore = signalStore(
  withState<FlowStoreState>(initialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    initialize(clientId: string, flowId: string) {
      patchState(store, {clientId, flowId});
    },
    fetchFlow() {
      const flow = store.flow();
      if (flow) {
        return;
      }
      const clientId = store.clientId();
      const flowId = store.flowId();
      if (clientId == null || flowId == null) {
        throw new Error(
          'Client ID and flow ID are not set. Call `initialize` first.',
        );
      }
      httpApiService
        .pollFlow(clientId, flowId, 0) // no polling.
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((flow: Flow) => {
          patchState(store, {flow});
        });
    },
    fetchFlowResults(resultType?: PayloadType) {
      const clientId = store.clientId();
      const flowId = store.flowId();
      if (clientId == null || flowId == null) {
        throw new Error(
          'Client ID and flow ID are not set. Call `initialize` first.',
        );
      }
      httpApiService
        .listResultsForFlow(
          {
            clientId,
            flowId,
            count: DEFAULT_COUNT_FLOW_RESULTS,
            offset: 0,
            withType: resultType,
          },
          0, // no polling.
        )
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((flowResults: ListFlowResultsResult) => {
          const flowResultsByPayloadType = new Map<PayloadType, FlowResult[]>();
          for (const flowResult of flowResults.results) {
            const payloadType = flowResult.payloadType;
            if (!payloadType) {
              continue;
            }
            if (!flowResultsByPayloadType.has(payloadType)) {
              flowResultsByPayloadType.set(payloadType, [flowResult]);
            } else {
              flowResultsByPayloadType.get(payloadType)!.push(flowResult);
            }
          }
          patchState(store, {
            flowResultsByPayloadType,
            countLoadedResults: flowResults.results.length,
            countTotalResults: flowResults.totalCount,
          });
        });
    },
    fetchFlowLogs() {
      const clientId = store.clientId();
      const flowId = store.flowId();
      if (clientId == null || flowId == null) {
        throw new Error(
          'Client ID and flow ID are not set. Call `initialize` first.',
        );
      }
      httpApiService
        .fetchFlowLogs(clientId, flowId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((logResult: FlowLogs) => {
          patchState(store, {
            logs: logResult.items ?? [],
          });
        });
    },
    fetchAllFlowOutputPluginLogs() {
      const clientId = store.clientId();
      const flowId = store.flowId();
      if (clientId == null || flowId == null) {
        throw new Error(
          'Client ID and flow ID are not set. Call `initialize` first.',
        );
      }

      httpApiService
        .listAllFlowOutputPluginLogs(clientId, flowId)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((result: ListAllOutputPluginLogsResult) => {
          patchState(store, {outputPluginLogs: result.items ?? []});
        });
    },
  })),
);
