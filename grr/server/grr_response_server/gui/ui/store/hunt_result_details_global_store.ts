import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable, of} from 'rxjs';
import {
  catchError,
  distinctUntilChanged,
  filter,
  map,
  switchMap,
  tap,
  withLatestFrom,
} from 'rxjs/operators';

import {
  ApiFlow,
  ApiHuntError,
  ApiHuntResult,
  ApiListHuntErrorsArgs,
  ApiListHuntResultsArgs,
} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateFlow} from '../lib/api_translation/flow';
import {getHuntResultKey} from '../lib/api_translation/hunt';
import {createOptionalDate} from '../lib/api_translation/primitive';
import {FlowWithDescriptor} from '../lib/models/flow';
import {
  HuntResultOrError,
  PayloadType,
  ResultKey,
  toResultKey,
  toResultKeyString,
  typeUrlToPayloadType,
} from '../lib/models/result';
import {isNonNull, isNull} from '../lib/preconditions';

import {ConfigGlobalStore} from './config_global_store';

/**
 * Number of items to fetch per request when searching for a Hunt result/error
 * details.
 */
export const RESULT_BATCH_COUNT = 50;

/** Function that beautifies JSON-like data or primitives into string. */
export function stringifyAndBeautify(
  value: Parameters<JSON['stringify']>[0],
): string {
  return JSON.stringify(value, null, 2);
}

const DATA_NOT_FOUND = 'Data not found';

function isHuntError(
  result: HuntResultOrError | undefined,
): result is ApiHuntError {
  return (
    isNonNull((result as ApiHuntError)?.logMessage) ||
    isNonNull((result as ApiHuntError)?.backtrace)
  );
}

function isHuntResult(
  result: HuntResultOrError | undefined,
): result is ApiHuntResult {
  return isNonNull((result as ApiHuntResult)?.payload);
}

function getPayloadFromHuntError(error: ApiHuntError): string {
  return stringifyAndBeautify({
    logMessage: error.logMessage,
    backtrace: error.backtrace,
  });
}

function getPayloadFromHuntResult(result: ApiHuntResult): string {
  return stringifyAndBeautify(result.payload);
}

function getDisplayFromHuntResultOrError(
  value: HuntResultOrError | undefined,
): string {
  if (isNonNull(value)) {
    if (isHuntResult(value)) return getPayloadFromHuntResult(value);
    if (isHuntError(value)) return getPayloadFromHuntError(value);
  }

  return DATA_NOT_FOUND;
}

function getPayloadTypeFromResultOrError(
  result: HuntResultOrError,
): PayloadType | undefined {
  if (isHuntResult(result)) {
    return typeUrlToPayloadType(result.payload?.['@type']);
  }

  if (isHuntError(result)) return PayloadType.API_HUNT_ERROR;

  return undefined;
}

declare interface HuntResultDetailsStoreState {
  resultKeyId?: string;
  payloadType?: PayloadType;
  resultOrErrorState: {
    value?: HuntResultOrError;
    stringifiedDisplayResult: string;
    isLoading: boolean;
  };
  flowState: {withDescriptor?: FlowWithDescriptor; isLoading: boolean};
}

/**
 * Store that holds the state of the result/error of a hunt and its
 * corresponding flow.
 */
class HuntResultDetailsStore extends ComponentStore<HuntResultDetailsStoreState> {
  private readonly shouldLoadResult$ = this.select((state) => state).pipe(
    filter(({resultKeyId, resultOrErrorState: oldResultOrErrorState}) => {
      if (isNull(resultKeyId) || oldResultOrErrorState.isLoading) {
        return false;
      }
      if (isNull(oldResultOrErrorState.value)) return true;

      const resultKey = toResultKey(resultKeyId);

      const huntId = resultKey.flowId;

      const oldResultKeyId = getHuntResultKey(
        oldResultOrErrorState.value,
        huntId,
      );

      return resultKeyId !== oldResultKeyId;
    }),
    // We stop the stream is the resultKeyId hasn't changed:
    distinctUntilChanged((oldState, newState) => {
      return oldState.resultKeyId === newState.resultKeyId;
    }),
    map((state) => ({
      resultKey: toResultKey(state.resultKeyId!),
      payloadType: state.payloadType,
    })),
  );

  readonly resultOrError$ = this.select(
    (state) => state.resultOrErrorState.value,
  );
  readonly filteredResultKeyId$ = this.select(
    (state) => state.resultKeyId,
  ).pipe(filter(isNonNull), distinctUntilChanged());
  readonly resultKey$ = this.filteredResultKeyId$.pipe(
    map((rkId) => toResultKey(rkId)),
  );
  readonly resultOrErrorDisplay$ = this.select(
    (state) => state.resultOrErrorState.stringifiedDisplayResult,
  );
  readonly flowWithDescriptor$ = this.select(
    (state) => state.flowState.withDescriptor,
  );
  readonly isFlowLoading$ = this.select((state) => state.flowState.isLoading);
  readonly isHuntResultLoading$ = this.select(
    (state) => state.resultOrErrorState.isLoading,
  );

  readonly selectHuntResult = this.updater<{
    resultOrError: HuntResultOrError;
    resultKeyId: string;
  }>((state, {resultOrError, resultKeyId}) => ({
    resultKeyId,
    type: getPayloadTypeFromResultOrError(resultOrError),
    resultOrErrorState: {
      value: resultOrError,
      stringifiedDisplayResult: getDisplayFromHuntResultOrError(resultOrError),
      isLoading: false,
    },
    flowState: {
      withDescriptor: undefined,
      isLoading: false,
    },
  }));

  readonly selectHuntResultId = this.updater<{
    resultKeyId: string;
    payloadType: PayloadType | undefined;
  }>((state, resultMetadata) => {
    if (state.resultKeyId === resultMetadata.resultKeyId) return state;

    return {
      ...state,
      resultKeyId: resultMetadata.resultKeyId,
      payloadType: resultMetadata.payloadType,
    };
  });

  readonly setFlowDescriptorFromFlow = this.effect<ApiFlow | undefined>(
    (obs$) =>
      obs$.pipe(
        withLatestFrom(this.configGlobalStore.flowDescriptors$),
        tap(([apiFlow, fds]) => {
          let flowWithDescriptor: FlowWithDescriptor | undefined;

          if (isNonNull(apiFlow)) {
            const type = apiFlow.args?.['@type'];

            flowWithDescriptor = {
              flow: translateFlow(apiFlow),
              descriptor: fds.get(apiFlow.name ?? ''),
              flowArgType: typeof type === 'string' ? type : undefined,
            };
          }

          this.patchState({
            flowState: {
              withDescriptor: flowWithDescriptor,
              isLoading: false,
            },
          });
        }),
      ),
  );

  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    super({
      resultKeyId: undefined,
      payloadType: undefined,
      resultOrErrorState: {
        value: undefined,
        stringifiedDisplayResult: DATA_NOT_FOUND,
        isLoading: false,
      },
      flowState: {
        withDescriptor: undefined,
        isLoading: false,
      },
    });

    this.filteredResultKeyId$
      .pipe(
        map((resultKey) => toResultKey(resultKey)),
        tap(() => {
          this.patchState({
            flowState: {
              isLoading: true,
              withDescriptor: undefined,
            },
          });
        }),
        switchMap((resultKey) =>
          this.httpApiService
            .fetchFlow(resultKey.clientId, resultKey.flowId)
            .pipe(catchError(() => of(undefined))),
        ),
      )
      .subscribe(this.setFlowDescriptorFromFlow);

    this.shouldLoadResult$
      .pipe(
        tap(() => {
          this.patchState({
            resultOrErrorState: {
              isLoading: true,
              value: undefined,
              stringifiedDisplayResult: DATA_NOT_FOUND,
            },
          });
        }),
        switchMap((resultMetadata) =>
          this.getHuntResultFromHuntResultKey(
            resultMetadata.resultKey,
            resultMetadata.payloadType,
          ).pipe(catchError(() => of(undefined))),
        ),
      )
      .subscribe((huntResultOrError) => {
        this.patchState({
          resultOrErrorState: {
            value: huntResultOrError,
            stringifiedDisplayResult:
              getDisplayFromHuntResultOrError(huntResultOrError),
            isLoading: false,
          },
        });
      });
  }

  private getHuntResultFromHuntResultKey(
    resultKey: ResultKey,
    payloadType?: PayloadType,
  ): Observable<HuntResultOrError | undefined> {
    const isHuntError = payloadType === PayloadType.API_HUNT_ERROR;
    const resultKeyId = toResultKeyString(resultKey);
    const params = this.getResultsOrErrorSearchParameters(
      resultKey,
      payloadType,
    );

    return this.recursiveSearchForHuntResult(params, resultKeyId, isHuntError);
  }

  private getResultsOrErrorSearchParameters(
    resultKey: ResultKey,
    payloadType?: PayloadType,
  ): ApiListHuntResultsArgs & ApiListHuntErrorsArgs {
    const isHuntError = payloadType === PayloadType.API_HUNT_ERROR;

    const params: ApiListHuntResultsArgs & ApiListHuntErrorsArgs = {
      huntId: resultKey.flowId,
      offset: `${0}`,
      count: `${RESULT_BATCH_COUNT}`,
    };

    if (isHuntError || !payloadType) return params;

    return {...params, withType: payloadType};
  }

  /**
   * This method will try to find the a specific Hunt Result by recursivelly
   * calling the backend for results/errors and then looking for it manually.
   */
  private recursiveSearchForHuntResult(
    params: ApiListHuntResultsArgs & ApiListHuntErrorsArgs,
    resultKeyId: string,
    isHuntError: boolean,
  ): Observable<HuntResultOrError | undefined> {
    const huntResultOrErrorList$: Observable<readonly HuntResultOrError[]> =
      isHuntError
        ? this.httpApiService.listErrorsForHunt(params)
        : this.httpApiService.listResultsForHunt(params);

    return huntResultOrErrorList$.pipe(
      catchError(() => of([])),
      switchMap((resultOrErrors) => {
        if (resultOrErrors.length === 0) return of(undefined);

        const huntResult = resultOrErrors.find(
          (roe) => getHuntResultKey(roe, params.huntId!) === resultKeyId,
        );

        if (huntResult) return of(huntResult);

        // If the batch is smaller than what we ask for, we assume the
        // hunt result/error wasn't found and we return undefined:
        if (resultOrErrors.length < RESULT_BATCH_COUNT) return of(undefined);

        const updatedParams: ApiListHuntResultsArgs = {
          ...params,
          offset: `${Number(params.offset) + RESULT_BATCH_COUNT}`,
        };

        return this.recursiveSearchForHuntResult(
          updatedParams,
          resultKeyId,
          isHuntError,
        );
      }),
    );
  }
}

/** Facade store/service to interact with HuntResultDetailsStore. */
@Injectable({
  providedIn: 'root',
})
export class HuntResultDetailsGlobalStore {
  constructor(
    private readonly httpApiService: HttpApiService,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    this.store = new HuntResultDetailsStore(
      this.httpApiService,
      this.configGlobalStore,
    );
    this.huntId$ = this.store.resultKey$.pipe(map((key) => key?.flowId));
    this.clientId$ = this.store.resultKey$.pipe(map((key) => key?.clientId));
    this.timestamp$ = this.store.resultKey$.pipe(
      map((key) => createOptionalDate(key?.timestamp ?? '')),
    );
    this.resultOrErrorDisplay$ = this.store.resultOrErrorDisplay$;
    this.flowWithDescriptor$ = this.store.flowWithDescriptor$;
    this.isFlowLoading$ = this.store.isFlowLoading$;
    this.isHuntResultLoading$ = this.store.isHuntResultLoading$;
  }

  private readonly store;

  readonly huntId$;
  readonly clientId$;
  readonly timestamp$;
  readonly resultOrErrorDisplay$;
  readonly flowWithDescriptor$;
  readonly isFlowLoading$;
  readonly isHuntResultLoading$;

  /** Selects a hunt result with a given id. */
  selectHuntResultId(resultKeyId: string, payloadType?: PayloadType): void {
    this.store.selectHuntResultId({resultKeyId, payloadType});
  }

  /**
   * Selects a "full" hunt result together with its corresponding key, to avoid
   * re-fetching it from the backend.
   */
  selectHuntResultOrError(
    resultOrError: HuntResultOrError,
    huntId: string,
  ): void {
    this.store.selectHuntResult({
      resultOrError,
      resultKeyId: getHuntResultKey(resultOrError, huntId),
    });
  }
}
