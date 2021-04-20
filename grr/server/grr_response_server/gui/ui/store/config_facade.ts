import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateArtifactDescriptor} from '@app/lib/api_translation/artifact';
import {translateFlowDescriptor} from '@app/lib/api_translation/flow';
import {Observable, of} from 'rxjs';
import {filter, map, shareReplay, switchMap, switchMapTo, tap} from 'rxjs/operators';

import {ApiUiConfig} from '../lib/api/api_interfaces';
import {getApiClientLabelName} from '../lib/api_translation/client';
import {cacheLatest} from '../lib/cache';
import {ApprovalConfig} from '../lib/models/client';
import {ArtifactDescriptor, ArtifactDescriptorMap, FlowDescriptor, FlowDescriptorMap} from '../lib/models/flow';
import {isNonNull} from '../lib/preconditions';

/** The state of the Config. */
export interface ConfigState {
  flowDescriptors?: FlowDescriptorMap;
  artifactDescriptors?: ArtifactDescriptorMap;
  approvalConfig?: ApprovalConfig;
  uiConfig?: ApiUiConfig;
  clientsLabels?: ReadonlyArray<string>;
}

/** ComponentStore implementation for the config facade. */
@Injectable({
  providedIn: 'root',
})
export class ConfigStore extends ComponentStore<ConfigState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  private readonly updateFlowDescriptors =
      this.updater<ReadonlyArray<FlowDescriptor>>((state, descriptors) => {
        return {
          ...state,
          flowDescriptors: new Map(descriptors.map(fd => [fd.name, fd])),
        };
      });

  private readonly updateArtifactDescriptors =
      this.updater<ReadonlyArray<ArtifactDescriptor>>((state, descriptors) => {
        return {
          ...state,
          artifactDescriptors: new Map(descriptors.map(ad => [ad.name, ad])),
        };
      });


  private readonly updateApprovalConfig =
      this.updater<ApprovalConfig>((state, approvalConfig) => {
        return {...state, approvalConfig};
      });

  private readonly updateClientsLabels =
      this.updater<string[]>((state, clientsLabels) => {
        return {...state, clientsLabels};
      });


  private readonly listFlowDescriptors = this.effect<void>(
      obs$ => obs$.pipe(
          switchMap(() => this.httpApiService.listFlowDescriptors()),
          map(apiDescriptors => apiDescriptors.map(translateFlowDescriptor)),
          tap(descriptors => {
            this.updateFlowDescriptors(descriptors);
          }),
          ));

  private readonly listArtifactDescriptors = this.effect<void>(
      obs$ => obs$.pipe(
          switchMap(() => this.httpApiService.listArtifactDescriptors()),
          cacheLatest('listArtifactDescriptors'),
          map(apiDescriptors =>
                  apiDescriptors.map(translateArtifactDescriptor)),
          tap(descriptors => {
            this.updateArtifactDescriptors(descriptors);
          }),
          ));

  private readonly fetchApprovalConfig = this.effect<void>(
      obs$ => obs$.pipe(
          switchMap(() => this.httpApiService.fetchApprovalConfig()),
          tap(approvalConfig => {
            this.updateApprovalConfig(approvalConfig);
          }),
          ));

  private readonly fetchClientsLabels = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.httpApiService.fetchAllClientsLabels()),
          /**
           * When fetching all labels the owner is not set in the API
           * implementation, so we extract only the label names
           */
          map(apiClientsLabels => apiClientsLabels.map(getApiClientLabelName)),
          tap(clientsLabels => {
            this.updateClientsLabels(clientsLabels);
          }),
          ));

  /** An observable emitting available flow descriptors. */
  readonly flowDescriptors$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.listFlowDescriptors();
      }),
      switchMap(() => this.select(state => state.flowDescriptors)),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  /** An observable emitting the approval configuration. */
  readonly approvalConfig$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.fetchApprovalConfig();
      }),
      switchMap(() => this.select(state => state.approvalConfig)),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  private readonly updateUiConfig =
      this.updater<ApiUiConfig>((state, uiConfig) => {
        return {...state, uiConfig};
      });

  private readonly fetchUiConfig = this.effect<void>(
      obs$ => obs$.pipe(
          switchMap(() => this.httpApiService.fetchUiConfig()),
          tap(uiConfig => {
            this.updateUiConfig(uiConfig);
          }),
          ));

  /** An observable emitting available flow descriptors. */
  readonly uiConfig$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.fetchUiConfig();
      }),
      switchMap(() => this.select(state => state.uiConfig)),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$ = of(undefined).pipe(
      tap(() => {
        this.fetchClientsLabels();
      }),
      switchMapTo(this.select(state => state.clientsLabels)),
      filter(
          (clientsLabels): clientsLabels is string[] =>
              clientsLabels !== undefined),
  );

  /** An observable emitting available flow descriptors. */
  readonly artifactDescriptors$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.listArtifactDescriptors();
      }),
      switchMap(() => this.select(state => state.artifactDescriptors)),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );
}


/** Facade to retrieve general purpose configuration and backend data. */
@Injectable({
  providedIn: 'root',
})
export class ConfigFacade {
  constructor(private readonly store: ConfigStore) {}

  /** An observable emitting available flow descriptors. */
  readonly flowDescriptors$: Observable<FlowDescriptorMap> =
      this.store.flowDescriptors$;

  /** An observable emitting the approval configuration. */
  readonly approvalConfig$: Observable<ApprovalConfig> =
      this.store.approvalConfig$;

  /** An observable emitting the UI configuration. */
  readonly uiConfig$: Observable<ApiUiConfig> = this.store.uiConfig$;

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$: Observable<string[]> = this.store.clientsLabels$;

  readonly artifactDescriptors$: Observable<ArtifactDescriptorMap> =
      this.store.artifactDescriptors$;
}
