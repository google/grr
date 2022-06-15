import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, NEVER, Observable, of} from 'rxjs';
import {filter, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {ApiHuntApproval, ForemanClientRuleSet, OutputPluginDescriptor} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {extractErrorMessage, RequestStatus, trackRequest} from '../lib/api/track_request';
import {translateFlow} from '../lib/api_translation/flow';
import {translateSafetyLimits} from '../lib/api_translation/hunt';
import {FlowWithDescriptor} from '../lib/models/flow';
import {SafetyLimits} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';

interface OriginalFlowParams {
  readonly clientId: string;
  readonly flowId: string;
}

interface NewHuntState {
  readonly originalFlowParams?: OriginalFlowParams;
  readonly huntId?: string;
  readonly huntRequestState?: RequestStatus<ApiHuntApproval, string>;
}

/** ComponentStore implementation used by the NewHuntLocalStore. */
class NewHuntComponentStore extends ComponentStore<NewHuntState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configGlobalStore: ConfigGlobalStore) {
    super({});
  }

  /** Reducer updating the store and setting the clientId and flowId. */
  readonly selectOriginalFlow = this.updater<OriginalFlowParams>(
      (state, originalFlowParams) => ({...state, originalFlowParams}));

  private readonly originalFlowParams$:
      Observable<OriginalFlowParams|undefined> =
          this.select(state => state.originalFlowParams);

  readonly flowWithDescriptor$: Observable<FlowWithDescriptor|undefined> =
      combineLatest(
          [this.originalFlowParams$, this.configGlobalStore.flowDescriptors$])
          .pipe(
              switchMap(([params, fds]) => {
                return params ?
                    this.httpApiService
                        .fetchFlow(params.clientId, params.flowId)
                        .pipe(
                            map(apiFlow => {
                              if (apiFlow) {
                                const type = apiFlow.args?.['@type'];
                                return {
                                  flow: translateFlow(apiFlow),
                                  descriptor: fds.get(apiFlow.name ?? ''),
                                  flowArgType: typeof type === 'string' ?
                                      type :
                                      undefined,
                                };
                              }
                              return undefined;
                            }),
                            ) :
                    of(undefined);
              }),
          );

  readonly safetyLimits$: Observable<SafetyLimits> =
      this.configGlobalStore.uiConfig$.pipe(
          map(config => config.defaultHuntRunnerArgs),
          filter(isNonNull),
          map(translateSafetyLimits),
      );

  /** An effect to run a hunt */
  readonly runHunt = this.effect<{
    description: string,
    safetyLimits: SafetyLimits,
    rules: ForemanClientRuleSet,
    outputPlugins: ReadonlyArray<OutputPluginDescriptor>
  }>(obs$ =>
         obs$.pipe(
             withLatestFrom(this.flowWithDescriptor$),
             switchMap(
                 ([opts, flowWithDescriptors]) => flowWithDescriptors ?
                     this.httpApiService.createHunt(
                         opts.description, flowWithDescriptors,
                         opts.safetyLimits, opts.rules, opts.outputPlugins) :
                     NEVER),
             tap(hunt => {
               this.updateHuntId(hunt?.huntId);
             }),
             ));

  private readonly updateHuntId =
      this.updater<string|undefined>((state, huntId) => ({...state, huntId}));

  readonly huntId$: Observable<string|undefined> =
      this.select(state => state.huntId);

  readonly huntRequestStatus$:
      Observable<RequestStatus<ApiHuntApproval, string>|undefined> =
          this.select(state => state.huntRequestState);

  /** An effect requesting a new hunt approval. */
  readonly requestHuntApproval =
      this.effect<{huntId: string, approvalArgs: ApiHuntApproval}>(
          obs$ => obs$.pipe(
              switchMap(
                  (opts) =>
                      trackRequest(this.httpApiService.requestHuntApproval(
                          opts.huntId, opts.approvalArgs))),
              tap(requestStatus => {
                this.updateHuntRequestStatus(requestStatus);
              }),
              ));

  private readonly updateHuntRequestStatus =
      this.updater<RequestStatus<ApiHuntApproval>>(
          (state, huntRequestState) => ({
            ...state,
            huntRequestState: extractErrorMessage(huntRequestState),
          }));
}

/** LocalStore for new hunt related API calls. */
@Injectable()
export class NewHuntLocalStore {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configGlobalStore: ConfigGlobalStore) {}

  private readonly store =
      new NewHuntComponentStore(this.httpApiService, this.configGlobalStore);

  /** Selects a flow with a given parameters. */
  selectOriginalFlow(clientId: string, flowId: string): void {
    this.store.selectOriginalFlow({clientId, flowId});
  }

  runHunt(
      description: string, safetyLimits: SafetyLimits,
      rules: ForemanClientRuleSet,
      outputPlugins: ReadonlyArray<OutputPluginDescriptor>): void {
    this.store.runHunt({description, safetyLimits, rules, outputPlugins});
  }

  requestHuntApproval(huntId: string, approvalArgs: ApiHuntApproval) {
    this.store.requestHuntApproval({huntId, approvalArgs});
  }
  readonly safetyLimits$ = this.store.safetyLimits$;
  readonly huntId$ = this.store.huntId$;
  readonly flowWithDescriptor$ = this.store.flowWithDescriptor$;
  readonly huntRequestStatus$ = this.store.huntRequestStatus$;
}
