import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Store} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateFlowDescriptor} from '@app/lib/api_translation/flow';
import {Observable, of} from 'rxjs';
import {filter, map, shareReplay, switchMap, switchMapTo, tap} from 'rxjs/operators';

import {ApprovalConfig, ClientLabel} from '../lib/models/client';
import {FlowDescriptor, FlowDescriptorMap} from '../lib/models/flow';
import {getApiClientLabelName} from '@app/lib/api_translation/client';


/** The state of the Config. */
export interface ConfigState {
  flowDescriptors?: FlowDescriptorMap;
  approvalConfig?: ApprovalConfig;
  clientsLabels?: string[];
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
          switchMapTo(this.httpApiService.listFlowDescriptors()),
          map(apiDescriptors => apiDescriptors.map(translateFlowDescriptor)),
          tap(descriptors => {
            this.updateFlowDescriptors(descriptors);
          }),
          ));

  private readonly fetchApprovalConfig = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.httpApiService.fetchApprovalConfig()),
          tap(approvalConfig => {
            this.updateApprovalConfig(approvalConfig);
          }),
          ));

  private readonly fetchClientsLabels = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.httpApiService.fetchAllClientsLabels()),
          map(apiClientsLabels =>
              apiClientsLabels.map(getApiClientLabelName)),
          tap(clientsLabels => this.updateClientsLabels(clientsLabels)),
        ));

  /** An observable emitting available flow descriptors. */
  readonly flowDescriptors$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.listFlowDescriptors();
      }),
      switchMap(() => this.select(state => state.flowDescriptors)),
      filter(
          (descriptors): descriptors is FlowDescriptorMap =>
              descriptors !== undefined),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  /** An observable emitting the approval configuration. */
  readonly approvalConfig$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.fetchApprovalConfig();
      }),
      switchMap(() => this.select(state => state.approvalConfig)),
      filter(
          (approvalConfig): approvalConfig is ApprovalConfig =>
              approvalConfig !== undefined),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$ = of(undefined).pipe(
      tap(() => this.fetchClientsLabels()),
      switchMapTo(this.select(state => state.clientsLabels)),
      filter((clientsLabels): clientsLabels is string[] =>
          clientsLabels !== undefined),
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

  /** An observable emitting a list of all clients labels. */
  readonly clientsLabels$: Observable<string[]> =
      this.store.clientsLabels$;
}
