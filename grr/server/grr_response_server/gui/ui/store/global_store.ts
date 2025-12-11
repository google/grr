import {computed, DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {
  patchState,
  signalStore,
  withComputed,
  withMethods,
  withState,
} from '@ngrx/signals';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {ApprovalConfig} from '../lib/models/client';
import {UiConfig} from '../lib/models/configuration';
import {
  ArtifactDescriptor,
  ArtifactDescriptorMap,
  Binary,
  BinaryType,
  FlowDescriptor,
} from '../lib/models/flow';
import {OutputPluginDescriptor} from '../lib/models/output_plugin';
import {GrrUser} from '../lib/models/user';

interface GlobalState {
  readonly currentUser: GrrUser | null;
  readonly uiConfig: UiConfig | null;
  readonly approvalConfig: ApprovalConfig | null;
  readonly webAuthType: string | null;
  readonly allLabels: readonly string[];
  readonly flowDescriptors: readonly FlowDescriptor[];
  readonly artifactDescriptorMap: ArtifactDescriptorMap;
  readonly binaries: readonly Binary[];
  readonly exportCommandPrefix: string | null;
  readonly outputPluginDescriptors: readonly OutputPluginDescriptor[];
}

const initialState: GlobalState = {
  currentUser: null,
  uiConfig: null,
  approvalConfig: null,
  webAuthType: null,
  allLabels: [],
  flowDescriptors: [],
  artifactDescriptorMap: new Map<string, ArtifactDescriptor>(),
  binaries: [],
  exportCommandPrefix: null,
  outputPluginDescriptors: [],
};

/**
 * Store for storing global state.
 * - This store is used to store global state that is shared across the app.
 * - This store is not tied to any component, and can be used by any component
 *   in the app.
 * - This store is not meant to be used to store data that is specific to a
 *   single component. For that, a component store should be used instead.
 * - initialize() method should be called once from the root component to
 *   initialize the store.
 */
// tslint:disable-next-line:enforce-name-casing
export const GlobalStore = signalStore(
  {providedIn: 'root'},
  withState(initialState),
  withMethods(
    (
      store,
      httpApiService = inject(HttpApiWithTranslationService),
      destroyRef = inject(DestroyRef),
    ) => ({
      initialize() {
        this.fetchCurrentUser();
        this.fetchUiConfig();
        this.fetchFlowDescriptors();
        this.fetchWebAuthType();
        this.getArtifactDescriptorMap();
        this.fetchAllLabels();
        this.fetchApprovalConfig();
        this.fetchExportCommandPrefix();
      },
      fetchCurrentUser() {
        httpApiService
          .fetchCurrentUser()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((currentUser: GrrUser) => {
            patchState(store, {currentUser});
          });
      },
      fetchUiConfig() {
        httpApiService
          .fetchUiConfig()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((uiConfig: UiConfig) => {
            patchState(store, {uiConfig});
          });
      },
      fetchApprovalConfig() {
        httpApiService
          .fetchApprovalConfig()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((approvalConfig: ApprovalConfig) => {
            patchState(store, {approvalConfig});
          });
      },
      fetchAllLabels() {
        httpApiService
          .fetchAllClientsLabels()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((labels: readonly string[]) => {
            patchState(store, {allLabels: labels});
          });
      },
      fetchFlowDescriptors() {
        httpApiService
          .listFlowDescriptors()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((flowDescriptors: readonly FlowDescriptor[]) => {
            patchState(store, {flowDescriptors});
          });
      },
      getArtifactDescriptorMap() {
        httpApiService
          .getArtifactDescriptorMap()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((artifactDescriptorMap: ArtifactDescriptorMap) => {
            patchState(store, {artifactDescriptorMap});
          });
      },
      fetchBinaryNames() {
        httpApiService
          .listBinaries(false)
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((binaries: readonly Binary[]) => {
            patchState(store, {binaries});
          });
      },
      fetchWebAuthType() {
        httpApiService
          .fetchWebAuthType()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((webAuthType: string) => {
            patchState(store, {webAuthType});
          });
      },
      fetchExportCommandPrefix() {
        httpApiService
          .fetchExportCommandPrefix()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe((exportCommandPrefix: string) => {
            patchState(store, {exportCommandPrefix});
          });
      },
      fetchOutputPluginDescriptors() {
        httpApiService
          .listOutputPluginDescriptors()
          .pipe(takeUntilDestroyed(destroyRef))
          .subscribe(
            (outputPluginDescriptors: readonly OutputPluginDescriptor[]) => {
              patchState(store, {outputPluginDescriptors});
            },
          );
      },
    }),
  ),
  withComputed((store) => ({
    flowDescriptorsMap: computed<Map<string, FlowDescriptor>>(() => {
      return new Map(store.flowDescriptors().map((fd) => [fd.name, fd]));
    }),
    pythonHacks: computed<Binary[]>(() => {
      return store
        .binaries()
        .filter((b) => b.type === BinaryType.PYTHON_HACK)
        .sort((a, b) => a.path.localeCompare(b.path));
    }),
    executables: computed<Binary[]>(() => {
      return store
        .binaries()
        .filter((b) => b.type === BinaryType.EXECUTABLE)
        .sort((a, b) => a.path.localeCompare(b.path));
    }),
  })),
);
