import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, Observable, of} from 'rxjs';
import {filter, map, shareReplay, startWith, switchMap, takeWhile, tap, withLatestFrom} from 'rxjs/operators';

import {ApiHunt, ForemanClientRuleSet, OutputPluginDescriptor} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateFlow} from '../lib/api_translation/flow';
import {translateHunt, translateSafetyLimits} from '../lib/api_translation/hunt';
import {FlowWithDescriptor} from '../lib/models/flow';
import {Hunt, SafetyLimits} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';

interface OriginalFlowRef {
  readonly clientId: string;
  readonly flowId: string;
}

interface NewHuntState {
  readonly originalFlowRef?: OriginalFlowRef;
  readonly originalHuntId?: string;
  readonly huntId?: string;
}

/** ComponentStore implementation used by the NewHuntLocalStore. */
class NewHuntComponentStore extends ComponentStore<NewHuntState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configGlobalStore: ConfigGlobalStore) {
    super({});
  }

  /** Reducer updating the store and setting the clientId and flowId. */
  readonly selectOriginalFlow = this.updater<OriginalFlowRef>(
      (state, originalFlowRef) => ({...state, originalFlowRef}));
  readonly selectOriginalHunt = this.updater<string>(
      (state, originalHuntId) => ({...state, originalHuntId}));

  private readonly originalFlowRef$: Observable<OriginalFlowRef|undefined> =
      this.select(state => state.originalFlowRef);
  private readonly originalHuntId$: Observable<string> =
      this.select(state => state.originalHuntId)
          .pipe(
              filter(isNonNull),
              shareReplay({bufferSize: 1, refCount: true}),
          );

  readonly originalHunt$: Observable<Hunt|null> = this.originalHuntId$.pipe(
      switchMap(huntId => {
        return this.httpApiService.fetchHunt(huntId).pipe(
            map((hunt: ApiHunt): Hunt => {
              const flowRef = hunt?.originalObject?.flowReference;
              if (flowRef && flowRef.clientId && flowRef.flowId) {
                this.selectOriginalFlow(
                    {clientId: flowRef.clientId, flowId: flowRef.flowId});
              }

              return translateHunt(hunt);
            }));
      }),
      startWith(null), shareReplay({bufferSize: 1, refCount: true}));

  readonly hasClientAccess$: Observable<boolean|undefined> =
      this.originalFlowRef$.pipe(
          switchMap(
              flowRef => (flowRef && flowRef.clientId) ?
                  this.httpApiService
                      .subscribeToVerifyClientAccess(flowRef.clientId)
                      .pipe(
                          takeWhile(hasAccess => !hasAccess, true),
                          startWith(undefined),
                          ) :
                  of(undefined)),
          shareReplay({bufferSize: 1, refCount: true}),
      );

  readonly flowWithDescriptor$: Observable<FlowWithDescriptor|null> =
      combineLatest([
        this.originalFlowRef$, this.hasClientAccess$,
        this.configGlobalStore.flowDescriptors$
      ])
          .pipe(
              switchMap(([flowRef, hasAccess, fds]) => {
                return flowRef && hasAccess ?
                    this.httpApiService
                        .fetchFlow(flowRef.clientId, flowRef.flowId)
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
                              return null;
                            }),
                            ) :
                    of(null);
              }),
              startWith(null),
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
             withLatestFrom(
                 this.flowWithDescriptor$, this.originalHunt$, this.state$),
             switchMap(
                 ([opts, flowWithDescriptors, originalHunt, state]) =>
                     this.httpApiService.createHunt(
                         opts.description, flowWithDescriptors, originalHunt,
                         opts.safetyLimits, opts.rules, opts.outputPlugins,
                         state.originalHuntId)),
             tap(hunt => {
               this.updateHuntId(hunt?.huntId);
             }),
             ));

  private readonly updateHuntId =
      this.updater<string|undefined>((state, huntId) => ({...state, huntId}));

  readonly huntId$: Observable<string|undefined> =
      this.select(state => state.huntId);
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
  selectOriginalHunt(huntId: string): void {
    this.store.selectOriginalHunt(huntId);
  }

  runHunt(
      description: string, safetyLimits: SafetyLimits,
      rules: ForemanClientRuleSet,
      outputPlugins: readonly OutputPluginDescriptor[]): void {
    this.store.runHunt({description, safetyLimits, rules, outputPlugins});
  }

  readonly safetyLimits$ = this.store.safetyLimits$;
  readonly huntId$ = this.store.huntId$;
  readonly flowWithDescriptor$ = this.store.flowWithDescriptor$;
  readonly originalHunt$ = this.store.originalHunt$;
}
