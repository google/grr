import {computed, DestroyRef, inject} from '@angular/core';
import {
  patchState,
  signalStore,
  withComputed,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';

import {
  ApiFlowReference,
  ApiHuntReference,
  ForemanClientRuleSet,
} from '../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {Flow} from '../lib/models/flow';
import {Hunt, SafetyLimits} from '../lib/models/hunt';
import {OutputPlugin} from '../lib/models/output_plugin';

interface NewFleetCollectionStoreState {
  originalFleetCollectionRef: ApiHuntReference | undefined;
  originalFlowRef: ApiFlowReference | undefined;
  originalFleetCollection: Hunt | undefined;
  originalFlow: Flow | undefined;
  newFleetCollection: Hunt | undefined;
}

function getInitialState(): NewFleetCollectionStoreState {
  return {
    originalFleetCollectionRef: undefined,
    originalFlowRef: undefined,
    originalFleetCollection: undefined,
    originalFlow: undefined,
    newFleetCollection: undefined,
  };
}

/**
 * Store for data of a single fleet collection.
 * The lifecycle of this store is tied to the FleetCollectionDetails component.
 */
// tslint:disable-next-line:enforce-name-casing
export const NewFleetCollectionStore = signalStore(
  withState<NewFleetCollectionStoreState>(getInitialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    initialize(
      fleetCollectionRef: ApiHuntReference | undefined,
      flowRef: ApiFlowReference | undefined,
    ) {
      if (!fleetCollectionRef && !flowRef) {
        throw new Error('Invalid reference provided to initialize the store.');
      }
      if (fleetCollectionRef && flowRef) {
        throw new Error(
          'Only one reference can be provided to initialize the store.',
        );
      }

      patchState(store, {
        ...getInitialState(),
        originalFleetCollectionRef: fleetCollectionRef,
        originalFlowRef: flowRef,
      });

      this.fetchRef();
    },
    fetchRef() {
      const fleetCollectionRef = store.originalFleetCollectionRef();
      const flowRef = store.originalFlowRef();
      if (fleetCollectionRef?.huntId) {
        httpApiService
          .fetchHunt(fleetCollectionRef.huntId, 0)
          .subscribe((fleetCollection) => {
            patchState(store, {originalFleetCollection: fleetCollection});
          });
      } else if (flowRef?.clientId && flowRef?.flowId) {
        httpApiService
          .fetchFlow(flowRef.clientId, flowRef.flowId)
          .subscribe((flow) => {
            patchState(store, {originalFlow: flow});
          });
      } else {
        throw new Error('Invalid reference provided to fetch the reference.');
      }
    },

    createFleetCollection(
      description: string,
      safetyLimits: SafetyLimits,
      rules: ForemanClientRuleSet,
      outputPlugins: readonly OutputPlugin[],
    ) {
      if (!store.originalFlowRef() && !store.originalFleetCollectionRef()) {
        throw new Error(
          'A flow reference is required to create a fleet collection.',
        );
      }
      const flowName =
        store.originalFlow()?.name ?? store.originalFleetCollection()?.flowName;

      if (!flowName) {
        throw new Error('Flow reference does not have a flow name.');
      }

      const flowArgs =
        store.originalFlow()?.args ?? store.originalFleetCollection()?.flowArgs;

      httpApiService
        .createHunt(
          description,
          flowName,
          flowArgs,
          store.originalFlowRef(),
          store.originalFleetCollectionRef(),
          safetyLimits,
          rules,
          outputPlugins,
        )
        .subscribe((fleetCollection) => {
          patchState(store, {newFleetCollection: fleetCollection});
        });
    },
  })),
  withComputed((store) => ({
    flowArgs: computed(() => {
      const flow = store.originalFlow();
      const fleetCollection = store.originalFleetCollection();
      if (flow) {
        return flow.args;
      } else if (fleetCollection) {
        return fleetCollection.flowArgs;
      } else {
        return undefined;
      }
    }),
    flowType: computed(() => {
      const flow = store.originalFlow();
      const fleetCollection = store.originalFleetCollection();
      if (flow) {
        return flow.flowType;
      } else if (fleetCollection) {
        return fleetCollection.flowType;
      } else {
        return undefined;
      }
    }),
  })),
);
