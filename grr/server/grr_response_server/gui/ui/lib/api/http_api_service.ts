import {
  HttpClient,
  HttpContext,
  HttpErrorResponse,
  HttpParams,
  HttpParamsOptions,
} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable, of, throwError, timer} from 'rxjs';
import {
  catchError,
  combineLatestWith,
  map,
  shareReplay,
  switchMap,
  take,
  takeLast,
  takeWhile,
} from 'rxjs/operators';

import {translateOutputPluginType} from '../../lib/api/translation/output_plugin';
import {ClientApprovalRequest} from '../../lib/models/client';
import {
  HuntApprovalKey,
  HuntApprovalRequest,
  SafetyLimits,
} from '../../lib/models/hunt';
import {OutputPlugin, OutputPluginType} from '../../lib/models/output_plugin';
import {assertNonNull} from '../preconditions';
import * as apiInterfaces from './api_interfaces';
import {TRACK_LOADING_STATE} from './http_interceptors/loading_interceptor';
import {POLLING_INTERVAL} from './http_interceptors/polling_interceptor';
import {
  SHOW_ERROR_BAR,
  SHOW_ERROR_BAR_FOR_403,
  SHOW_ERROR_BAR_FOR_404,
} from './http_interceptors/show_error_bar_interceptor';

/** Default polling interval for API calls. */
export const DEFAULT_POLLING_INTERVAL = 5000;

/**
 * Parameters of the listResultsForFlow call.
 */
export interface FlowResultsParams {
  readonly clientId: string;
  readonly flowId: string;
  readonly offset?: number;
  readonly count: number;
  readonly withType?: string;
  readonly withTag?: string;
}

/**
 * Flow results array attributed to a particular flow id and request params.
 */
export interface FlowResultsWithSourceParams {
  readonly params: FlowResultsParams;
  readonly results: readonly apiInterfaces.ApiFlowResult[];
}

/**
 * Common prefix for all API calls.
 */
export const URL_PREFIX = '/api/v2';

/**
 * Key to identify a ClientApproval.
 */
export interface ClientApprovalKey {
  readonly clientId: string;
  readonly approvalId: string;
  readonly requestor: string;
}

/** Access denied because the requestor is missing a valid approval. */
export class MissingApprovalError extends Error {
  constructor(response: HttpErrorResponse) {
    super(response.error?.message ?? response.message);
  }
}

/** Specification of a file. */
export interface FileSpec {
  readonly clientId: string;
  readonly pathType: apiInterfaces.PathSpecPathType;
  readonly path: string;
}

/** Arguments of GetFileText API call. */
export interface GetFileTextOptions {
  readonly offset?: apiInterfaces.ProtoInt64;
  readonly length?: apiInterfaces.ProtoInt64;
  readonly timestamp?: Date;
  readonly encoding?: apiInterfaces.ApiGetFileTextArgsEncoding;
}

/** Arguments of GetFileBlob API call. */
export interface GetFileBlobOptions {
  readonly offset?: apiInterfaces.ProtoInt64;
  readonly length?: apiInterfaces.ProtoInt64;
  readonly timestamp?: Date;
}

interface HttpParamsObject {
  [key: string]: null | undefined | number | bigint | boolean | string | Date;
}

function toHttpParams(o: HttpParamsObject): HttpParams {
  const params: HttpParamsOptions['fromObject'] = {};

  for (let [key, value] of Object.entries(o)) {
    if (value === null || value === undefined) {
      continue;
    } else if (typeof value === 'bigint') {
      value = value.toString();
    } else if (value instanceof Date) {
      value = value.getTime() * 1000;
    }

    params[key] = value;
  }

  return new HttpParams({fromObject: params});
}

function error404To<T>(replacement: T) {
  return (err: HttpErrorResponse) =>
    err.status === 404 ? of(replacement) : throwError(() => err);
}

/**
 * Service to make HTTP requests to GRR API endpoint.
 */
@Injectable()
export class HttpApiService {
  constructor(private readonly http: HttpClient) {
    this.flowDescriptors$ = this.http
      .get<apiInterfaces.ApiListFlowDescriptorsResult>(
        `${URL_PREFIX}/flows/descriptors`,
        {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
      )
      .pipe(
        map((res) => res.items ?? []),
        shareReplay(1), // Cache latest FlowDescriptors.
      );

    this.outputPluginDescriptors$ = this.http
      .get<apiInterfaces.ApiListOutputPluginDescriptorsResult>(
        `${URL_PREFIX}/output-plugins/all`,
        {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
      )
      .pipe(
        map((res) => res.items ?? []),
        shareReplay(1), // Cache latest OutputPluginDescriptors.
      );
  }

  /**
   * Searches for clients using given API arguments.
   */
  searchClients(
    args: apiInterfaces.ApiSearchClientsArgs,
  ): Observable<apiInterfaces.ApiSearchClientsResult> {
    let params = new HttpParams().set('query', args.query || '');
    if (args.offset) {
      params = params.set('offset', args.offset.toString());
    }
    if (args.count) {
      params = params.set('count', args.count.toString());
    }

    return this.http.get<apiInterfaces.ApiSearchClientsResult>(
      `${URL_PREFIX}/clients`,
      {params},
    );
  }

  fetchClient(
    id: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiClient> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true);
    return this.http.get<apiInterfaces.ApiClient>(
      `${URL_PREFIX}/clients/${id}`,
      {context},
    );
  }

  /** Requests approval to give the current user access to a client. */
  requestClientApproval(
    args: ClientApprovalRequest,
  ): Observable<apiInterfaces.ApiClientApproval> {
    const request: apiInterfaces.ApiCreateClientApprovalArgs = {
      clientId: args.clientId,
      approval: {
        reason: args.reason,
        notifiedUsers: args.approvers,
        emailCcAddresses: args.cc,
        expirationTimeUs: args.expirationTimeUs,
      },
    };

    return this.http.post<apiInterfaces.ApiClientApproval>(
      `${URL_PREFIX}/users/me/approvals/client/${args.clientId}`,
      request,
      {context: new HttpContext().set(TRACK_LOADING_STATE, true)},
    );
  }

  fetchApprovalConfig(): Observable<apiInterfaces.ApiConfigOption> {
    return this.http.get<apiInterfaces.ApiConfigOption>(
      `${URL_PREFIX}/config/Email.approval_optional_cc_address`,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  /**
   * Gets the currently configured web authentication type used by Admin UI.
   */
  fetchWebAuthType(): Observable<apiInterfaces.ApiConfigOption> {
    return this.http.get<apiInterfaces.ApiConfigOption>(
      `${URL_PREFIX}/config/AdminUI.webauth_manager`,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  /**
   * Gets the currently configured export command prefix from Admin UI.
   */
  fetchExportCommandPrefix(): Observable<apiInterfaces.ApiConfigOption> {
    return this.http.get<apiInterfaces.ApiConfigOption>(
      `${URL_PREFIX}/config/AdminUI.export_command`,
    );
  }

  /** Lists ClientApprovals in reversed chronological order. */
  listClientApprovals(
    clientId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListClientApprovalsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    return this.http.get<apiInterfaces.ApiListClientApprovalsResult>(
      `${URL_PREFIX}/users/me/approvals/client/${clientId}`,
      {context},
    );
  }

  verifyClientAccess(clientId: string): Observable<{}> {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_403, false);
    return this.http.head<{}>(`${URL_PREFIX}/clients/${clientId}/access`, {
      context,
    });
  }

  /** Fetches a ClientApproval. */
  fetchClientApproval(
    {clientId, requestor, approvalId}: ClientApprovalKey,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiClientApproval> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    return this.http.get<apiInterfaces.ApiClientApproval>(
      `${URL_PREFIX}/users/${requestor}/approvals/client/${clientId}/${approvalId}`,
      {context},
    );
  }

  /** Fetches a Flow. */
  fetchFlow(
    clientId: string,
    flowId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiFlow> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true);

    return this.http.get<apiInterfaces.ApiFlow>(
      `${URL_PREFIX}/clients/${clientId}/flows/${flowId}`,
      {context},
    );
  }

  fetchFlowLogs(
    clientId: string,
    flowId: string,
  ): Observable<apiInterfaces.ApiListFlowLogsResult> {
    return this.http.get<apiInterfaces.ApiListFlowLogsResult>(
      `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/log`,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  listAllFlowOutputPluginLogs(
    clientId: string,
    flowId: string,
  ): Observable<apiInterfaces.ApiListAllFlowOutputPluginLogsResult> {
    return this.http.get<apiInterfaces.ApiListAllFlowOutputPluginLogsResult>(
      `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/output-plugins/logs`,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  createHunt(
    description: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
    originalFlowRef: apiInterfaces.ApiFlowReference | undefined,
    originalHuntRef: apiInterfaces.ApiHuntReference | undefined,
    safetyLimits: SafetyLimits,
    rules: apiInterfaces.ForemanClientRuleSet,
    outputPlugins: readonly OutputPlugin[],
  ): Observable<apiInterfaces.ApiHunt> {
    if (!originalFlowRef && !originalHuntRef) {
      throw new Error('One of originalFlowRef or originalHuntRef must be set.');
    }
    if (originalFlowRef && originalHuntRef) {
      throw new Error(
        'Only one of originalFlowRef or originalHuntRef can be set.',
      );
    }

    const outputPluginDescriptors$: Observable<
      readonly apiInterfaces.OutputPluginDescriptor[]
    > = this.listOutputPluginDescriptors().pipe(
      map((descriptors) => {
        const pluginDescriptors: apiInterfaces.OutputPluginDescriptor[] = [];
        for (const plugin of outputPlugins) {
          if (plugin.pluginType === OutputPluginType.UNKNOWN) {
            continue;
          }
          const descriptor = descriptors.find(
            (d) =>
              translateOutputPluginType(d.name ?? '') === plugin.pluginType,
          );
          if (!descriptor) {
            throw new Error(`Output plugin ${plugin.pluginType} not found.`);
          }
          pluginDescriptors.push({
            pluginName: descriptor.name,
            args: {
              '@type': descriptor.argsType,
              ...plugin.args,
            },
          });
        }
        return pluginDescriptors;
      }),
    );

    const flowDescriptor$: Observable<apiInterfaces.ApiFlowDescriptor> =
      this.listFlowDescriptors().pipe(
        // Take FlowDescriptors at most once, so that Flows are not started
        // repeatedly if FlowDescriptors are ever updated.
        take(1),
        map(findFlowDescriptor(flowName)),
      );

    return flowDescriptor$.pipe(
      combineLatestWith(outputPluginDescriptors$),
      switchMap(([flowDescriptor, outputPluginDescriptors]) => {
        const huntRunnerArgs: apiInterfaces.HuntRunnerArgs = {
          description,
          clientRate: safetyLimits.clientRate,
          clientLimit: safetyLimits.clientLimit?.toString(),
          crashLimit: safetyLimits.crashLimit?.toString(),
          expiryTime: safetyLimits.expiryTime?.toString(),
          avgResultsPerClientLimit:
            safetyLimits.avgResultsPerClientLimit?.toString(),
          avgCpuSecondsPerClientLimit:
            safetyLimits.avgCpuSecondsPerClientLimit?.toString(),
          avgNetworkBytesPerClientLimit:
            safetyLimits.avgNetworkBytesPerClientLimit?.toString(),
          perClientCpuLimit: safetyLimits.perClientCpuLimit?.toString(),
          perClientNetworkLimitBytes:
            safetyLimits.perClientNetworkBytesLimit?.toString(),
          outputPlugins: outputPluginDescriptors,
          clientRuleSet: rules,
        };
        const request: apiInterfaces.ApiCreateHuntArgs = {
          flowName,
          flowArgs: {
            '@type': flowDescriptor.defaultArgs?.['@type'],
            ...flowArgs,
          },
          originalFlow: originalFlowRef,
          originalHunt: originalHuntRef,
          huntRunnerArgs,
        };
        return this.http
          .post<apiInterfaces.ApiHunt>(`${URL_PREFIX}/hunts`, request, {
            context: new HttpContext()
              .set(SHOW_ERROR_BAR, true)
              .set(TRACK_LOADING_STATE, true),
          })
          .pipe(
            catchError((e: HttpErrorResponse) => {
              throw new Error(e.error.message ?? e.message);
            }),
          );
      }),
    );
  }

  requestHuntApproval(
    args: HuntApprovalRequest,
  ): Observable<apiInterfaces.ApiHuntApproval> {
    const request: apiInterfaces.ApiCreateHuntApprovalArgs = {
      huntId: args.huntId,
      approval: {
        reason: args.reason,
        notifiedUsers: args.approvers,
        emailCcAddresses: args.cc,
      },
    };
    return this.http.post<apiInterfaces.ApiHuntApproval>(
      `${URL_PREFIX}/users/me/approvals/hunt/${args.huntId}`,
      request,
      {context: new HttpContext().set(TRACK_LOADING_STATE, true)},
    );
  }

  /** Lists HuntApprovals in reversed chronological order. */
  listHuntApprovals(
    huntId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListHuntApprovalsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    return this.http.get<apiInterfaces.ApiListHuntApprovalsResult>(
      `${URL_PREFIX}/users/me/approvals/hunt/${huntId}`,
      {context},
    );
  }

  /** Fetches a Hunt. */
  fetchHunt(
    id: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiHunt> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true);
    return this.http.get<apiInterfaces.ApiHunt>(`${URL_PREFIX}/hunts/${id}`, {
      context,
    });
  }

  verifyHuntAccess(huntId: string): Observable<{}> {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_403, false);
    return this.http.head<{}>(`${URL_PREFIX}/hunts/${huntId}/access`, {
      context,
    });
  }

  /** Fetches a HuntApproval */
  fetchHuntApproval(
    {huntId, approvalId, requestor}: HuntApprovalKey,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiHuntApproval> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    return this.http.get<apiInterfaces.ApiHuntApproval>(
      `${URL_PREFIX}/users/${requestor}/approvals/hunt/${huntId}/${approvalId}`,
      {context},
    );
  }

  /** Grants a HuntApproval. */
  grantHuntApproval({
    huntId,
    approvalId,
    requestor,
  }: HuntApprovalKey): Observable<apiInterfaces.ApiHuntApproval> {
    const context = new HttpContext().set(TRACK_LOADING_STATE, true);
    return this.http.post<apiInterfaces.ApiHuntApproval>(
      `${URL_PREFIX}/users/${requestor}/approvals/hunt/${huntId}/${approvalId}/actions/grant`,
      {},
      {context},
    );
  }

  patchHunt(
    huntId: string,
    patch: {
      state?: apiInterfaces.ApiHuntState;
      clientLimit?: bigint;
      clientRate?: number;
    },
  ): Observable<apiInterfaces.ApiHunt> {
    const params: apiInterfaces.ApiHunt = {
      'state': patch.state,
      'clientLimit': patch.clientLimit?.toString(),
      'clientRate': patch.clientRate,
    };
    return this.http.patch<apiInterfaces.ApiHunt>(
      `${URL_PREFIX}/hunts/${huntId}`,
      params,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  getHuntResultsByType(
    huntId: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiCountHuntResultsByTypeResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(TRACK_LOADING_STATE, true)
      .set(SHOW_ERROR_BAR, true);
    return this.http.get<apiInterfaces.ApiCountHuntResultsByTypeResult>(
      `${URL_PREFIX}/hunts/${huntId}/result-counts`,
      {context},
    );
  }

  /** Lists results of the given hunt. */
  listResultsForHunt(
    params: apiInterfaces.ApiListHuntResultsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListHuntResultsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(TRACK_LOADING_STATE, true)
      .set(SHOW_ERROR_BAR, true);
    const huntId = params.huntId;
    assertNonNull(huntId);

    const options: {[key: string]: number | string} = {};
    if (params.count) {
      options['count'] = params.count;
    }

    if (params.withType) {
      // TODO: Use camelCased field name once the backend converts
      // camelCased names to their snake_case counterpart.
      options['with_type'] = params.withType;
    }

    if (params.offset) {
      options['offset'] = params.offset;
    }

    const httpParams = new HttpParams({
      fromObject: {
        'huntId': huntId,
        ...options,
      },
    });

    return this.http
      .get<apiInterfaces.ApiListHuntResultsResult>(
        `${URL_PREFIX}/hunts/${params.huntId}/results`,
        {params: httpParams, context},
      )
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 403) {
            return throwError(() => new MissingApprovalError(err));
          } else {
            return throwError(() => err);
          }
        }),
      );
  }

  /** Lists errors of the given hunt. */
  listErrorsForHunt(
    params: apiInterfaces.ApiListHuntErrorsArgs,
  ): Observable<apiInterfaces.ApiListHuntErrorsResult> {
    const huntId = params.huntId;
    assertNonNull(huntId);

    const options: {[key: string]: number | string} = {};
    if (params.count) {
      options['count'] = params.count;
    }

    if (params.offset) {
      options['offset'] = params.offset;
    }

    const httpParams = new HttpParams({
      fromObject: {
        'huntId': huntId,
        ...options,
      },
    });

    return this.http
      .get<apiInterfaces.ApiListHuntErrorsResult>(
        `${URL_PREFIX}/hunts/${params.huntId}/errors`,
        {
          params: httpParams,
          context: new HttpContext()
            .set(SHOW_ERROR_BAR, true)
            .set(TRACK_LOADING_STATE, true),
        },
      )
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 403) {
            return throwError(() => new MissingApprovalError(err));
          } else {
            return throwError(() => err);
          }
        }),
      );
  }

  getHuntClientCompletionStats(
    args: apiInterfaces.ApiGetHuntClientCompletionStatsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiGetHuntClientCompletionStatsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(TRACK_LOADING_STATE, true)
      .set(SHOW_ERROR_BAR, true);

    const httpParams = args.size
      ? new HttpParams({fromObject: {'size': args.size}})
      : {};

    return this.http.get<apiInterfaces.ApiGetHuntClientCompletionStatsResult>(
      `${URL_PREFIX}/hunts/${args.huntId}/client-completion-stats`,
      {params: httpParams, context},
    );
  }

  // TODO: GET parameters require snake_case not camelCase
  // parameters. Do not allow createdBy and other camelCase parameters until
  // fixed.
  listHunts(
    args: apiInterfaces.ApiListHuntsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListHuntsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(TRACK_LOADING_STATE, true)
      .set(SHOW_ERROR_BAR, true);
    // TODO: Use camelCased field name once the backend converts
    // camelCased names to their snake_case counterpart.
    const params = toHttpParams({
      'offset': args.offset,
      'count': args.count,
      'robot_filter': args.robotFilter,
      'with_state': args.withState,
      'with_full_summary': true,
    });
    return this.http.get<apiInterfaces.ApiListHuntsResult>(
      `${URL_PREFIX}/hunts`,
      {params, context},
    );
  }

  fetchHuntLogs(
    huntId: string,
  ): Observable<apiInterfaces.ApiListHuntLogsResult> {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    return this.http.get<apiInterfaces.ApiListHuntLogsResult>(
      `${URL_PREFIX}/hunts/${huntId}/log`,
      {context},
    );
  }

  /** Grants a ClientApproval. */
  grantClientApproval({
    clientId,
    requestor,
    approvalId,
  }: ClientApprovalKey): Observable<apiInterfaces.ApiClientApproval> {
    const context = new HttpContext().set(TRACK_LOADING_STATE, true);
    return this.http.post<apiInterfaces.ApiClientApproval>(
      `${URL_PREFIX}/users/${requestor}/approvals/client/${clientId}/${approvalId}/actions/grant`,
      {},
      {context},
    );
  }

  private readonly flowDescriptors$;

  private readonly outputPluginDescriptors$;

  listFlowDescriptors(): Observable<
    readonly apiInterfaces.ApiFlowDescriptor[]
  > {
    return this.flowDescriptors$;
  }

  listOutputPluginDescriptors(): Observable<
    readonly apiInterfaces.ApiOutputPluginDescriptor[]
  > {
    return this.outputPluginDescriptors$;
  }

  listArtifactDescriptors(): Observable<apiInterfaces.ApiListArtifactsResult> {
    return this.http.get<apiInterfaces.ApiListArtifactsResult>(
      `${URL_PREFIX}/artifacts`,
      {
        context: new HttpContext().set(SHOW_ERROR_BAR, true),
      },
    );
  }

  listFlowsForClient(
    args: apiInterfaces.ApiListFlowsArgs,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListFlowsResult> {
    const clientId = args.clientId;
    assertNonNull(clientId);

    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true);

    // TODO: Use camelCased field name once the backend converts
    // camelCased names to their snake_case counterpart.
    const params = toHttpParams({
      'offset': args.offset,
      'count': args.count,
      'top_flows_only': args.topFlowsOnly,
      'min_started_at': args.minStartedAt,
      'max_started_at': args.maxStartedAt,
      'human_flows_only': args.humanFlowsOnly,
    });

    return this.http
      .get<apiInterfaces.ApiListFlowsResult>(
        `${URL_PREFIX}/clients/${clientId}/flows`,
        {params, context},
      )
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 403) {
            return throwError(() => new MissingApprovalError(err));
          } else {
            return throwError(() => err);
          }
        }),
      );
  }

  /** Lists all scheduled flows for the given client and user. */
  listScheduledFlows(
    clientId: string,
    creator: string,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListScheduledFlowsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true);

    return this.http.get<apiInterfaces.ApiListScheduledFlowsResult>(
      `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${creator}`,
      {context},
    );
  }

  /** Lists results of the given flow. */
  listResultsForFlow(
    params: FlowResultsParams,
    pollingInterval = 0,
  ): Observable<apiInterfaces.ApiListFlowResultsResult> {
    const context = new HttpContext()
      .set(POLLING_INTERVAL, pollingInterval)
      .set(SHOW_ERROR_BAR, true)
      .set(TRACK_LOADING_STATE, true);
    const options: {[key: string]: string} = {};
    if (params.withTag) {
      options['with_tag'] = params.withTag;
    }
    if (params.withType) {
      options['with_type'] = params.withType;
    }

    const httpParams = new HttpParams({
      fromObject: {
        'offset': (params.offset ?? 0).toString(),
        'count': params.count.toString(),
        ...options,
      },
    });

    return this.http.get<apiInterfaces.ApiListFlowResultsResult>(
      `${URL_PREFIX}/clients/${params.clientId}/flows/${params.flowId}/results`,
      {params: httpParams, context},
    );
  }

  /** Starts a Flow on the given Client. */
  startFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
    disableRrgSupport = false,
  ): Observable<apiInterfaces.ApiFlow> {
    return this.listFlowDescriptors().pipe(
      // Take FlowDescriptors at most once, so that Flows are not started
      // repeatedly if FlowDescriptors are ever updated.
      take(1),
      map(findFlowDescriptor(flowName)),
      map((fd) => ({
        clientId,
        flow: {
          name: flowName,
          args: {
            '@type': fd.defaultArgs?.['@type'],
            ...flowArgs,
          },
          runnerArgs: {
            'disableRrgSupport': disableRrgSupport,
          },
        },
      })),
      switchMap((request: apiInterfaces.ApiCreateFlowArgs) => {
        return this.http
          .post<apiInterfaces.ApiFlow>(
            `${URL_PREFIX}/clients/${clientId}/flows`,
            request,
            {
              context: new HttpContext()
                .set(SHOW_ERROR_BAR, true)
                .set(TRACK_LOADING_STATE, true),
            },
          )
          .pipe(
            catchError((e: HttpErrorResponse) =>
              throwError(new Error(e.error.message ?? e.message)),
            ),
          );
      }),
    );
  }

  /** Schedules a Flow on the given Client. */
  scheduleFlow(
    clientId: string,
    flowName: string,
    flowArgs: apiInterfaces.Any,
  ): Observable<apiInterfaces.ApiScheduledFlow> {
    return this.listFlowDescriptors().pipe(
      // Take FlowDescriptors at most once, so that Flows are not scheduled
      // repeatedly if FlowDescriptors are ever updated.
      take(1),
      map(findFlowDescriptor(flowName)),
      map((fd) => ({
        clientId,
        flow: {
          name: flowName,
          args: {
            '@type': fd.defaultArgs?.['@type'],
            ...flowArgs,
          },
        },
      })),
      switchMap((request: apiInterfaces.ApiCreateFlowArgs) => {
        return this.http
          .post<apiInterfaces.ApiFlow>(
            `${URL_PREFIX}/clients/${clientId}/scheduled-flows`,
            request,
            {
              context: new HttpContext()
                .set(SHOW_ERROR_BAR, true)
                .set(TRACK_LOADING_STATE, true),
            },
          )
          .pipe(
            catchError((e: HttpErrorResponse) =>
              throwError(() => new Error(e.error.message ?? e.message)),
            ),
          );
      }),
    );
  }

  /** Cancels the given Flow. */
  cancelFlow(
    clientId: string,
    flowId: string,
  ): Observable<apiInterfaces.ApiFlow> {
    const url = `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/actions/cancel`;
    return this.http.post<apiInterfaces.ApiFlow>(
      url,
      {},
      {
        context: new HttpContext().set(SHOW_ERROR_BAR, true),
      },
    );
  }

  /** Unschedules a previously scheduled flow. */
  unscheduleFlow(clientId: string, scheduledFlowId: string): Observable<{}> {
    const url = `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${scheduledFlowId}`;
    return this.http.delete<{}>(url, {
      context: new HttpContext().set(SHOW_ERROR_BAR, true),
    });
  }

  /** Fetches the current user. */
  fetchCurrentUser(): Observable<apiInterfaces.ApiGrrUser> {
    return this.http.get<apiInterfaces.ApiGrrUser>(`${URL_PREFIX}/users/me`, {
      context: new HttpContext().set(SHOW_ERROR_BAR, true),
    });
  }

  /** Explains a GlobExpression. */
  explainGlobExpression(
    clientId: string,
    globExpression: string,
    {exampleCount}: {exampleCount: number},
  ): Observable<apiInterfaces.ApiExplainGlobExpressionResult> {
    const url = `${URL_PREFIX}/clients/${clientId}/glob-expressions:explain`;
    const args: apiInterfaces.ApiExplainGlobExpressionArgs = {
      globExpression,
      exampleCount,
    };
    return this.http.post<apiInterfaces.ApiExplainGlobExpressionResult>(
      url,
      args,
      {
        context: new HttpContext().set(SHOW_ERROR_BAR, true),
      },
    );
  }

  fetchUiConfig(): Observable<apiInterfaces.ApiUiConfig> {
    return this.http.get<apiInterfaces.ApiUiConfig>(`${URL_PREFIX}/config/ui`, {
      context: new HttpContext().set(SHOW_ERROR_BAR, true),
    });
  }

  addClientLabel(clientId: string, label: string): Observable<{}> {
    const url = `${URL_PREFIX}/clients/labels/add`;
    const body: apiInterfaces.ApiAddClientsLabelsArgs = {
      clientIds: [clientId],
      labels: [label],
    };
    return this.http.post<{}>(url, body, {
      context: new HttpContext().set(SHOW_ERROR_BAR, true),
    });
  }

  removeClientLabel(clientId: string, label: string): Observable<{}> {
    const url = `${URL_PREFIX}/clients/labels/remove`;
    const body: apiInterfaces.ApiRemoveClientsLabelsArgs = {
      clientIds: [clientId],
      labels: [label],
    };
    return this.http
      .post<{}>(url, body, {
        context: new HttpContext().set(SHOW_ERROR_BAR, true),
      })
      .pipe(
        catchError((e: HttpErrorResponse) =>
          throwError(() => new Error(e.error.message ?? e.message)),
        ),
      );
  }

  fetchAllClientsLabels(): Observable<readonly apiInterfaces.ClientLabel[]> {
    const url = `${URL_PREFIX}/clients/labels`;
    return this.http
      .get<apiInterfaces.ApiListClientsLabelsResult>(url, {
        context: new HttpContext().set(SHOW_ERROR_BAR, true),
      })
      .pipe(
        map((clientsLabels) => clientsLabels.items ?? []),
        shareReplay(1),
      );
  }

  fetchClientSnapshots(
    clientId: string,
    start?: Date,
    end?: Date,
  ): Observable<apiInterfaces.ApiGetClientSnapshotsResult> {
    const url = `${URL_PREFIX}/clients/${clientId}/snapshots`;

    const params = new HttpParams({
      fromObject: {
        // If start not set, fetch from 1 second from epoch.
        'start': ((start?.getTime() ?? 1000) * 1000).toString(),
        'end': ((end ?? new Date()).getTime() * 1000).toString(),
      },
    });

    return this.http.get<apiInterfaces.ApiGetClientSnapshotsResult>(url, {
      params,
      context: new HttpContext()
        .set(SHOW_ERROR_BAR, true)
        .set(TRACK_LOADING_STATE, true),
    });
  }

  fetchClientStartupInfos(
    clientId: string,
    start?: Date,
    end?: Date,
  ): Observable<apiInterfaces.ApiGetClientStartupInfosResult> {
    const url = `${URL_PREFIX}/clients/${clientId}/startup-infos`;

    const params = new HttpParams({
      fromObject: {
        // If start not set, fetch from 1 second from epoch.
        'start': ((start?.getTime() ?? 1000) * 1000).toString(),
        'end': ((end ?? new Date()).getTime() * 1000).toString(),
        'exclude_snapshot_collections': true,
      },
    });

    return this.http.get<apiInterfaces.ApiGetClientStartupInfosResult>(url, {
      params,
      context: new HttpContext()
        .set(SHOW_ERROR_BAR, true)
        .set(TRACK_LOADING_STATE, true),
    });
  }

  suggestApprovers(
    usernameQuery: string,
  ): Observable<apiInterfaces.ApiListApproverSuggestionsResult> {
    const params = new HttpParams().set('username_query', usernameQuery);
    return this.http.get<apiInterfaces.ApiListApproverSuggestionsResult>(
      `${URL_PREFIX}/users/approver-suggestions`,
      {
        params,
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(TRACK_LOADING_STATE, true),
      },
    );
  }

  listRecentClientApprovals(parameters: {
    count?: number;
  }): Observable<apiInterfaces.ApiListClientApprovalsResult> {
    return this.http.get<apiInterfaces.ApiListClientApprovalsResult>(
      `${URL_PREFIX}/users/me/approvals/client`,
      {
        params: objectToHttpParams(parameters),
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(TRACK_LOADING_STATE, true),
      },
    );
  }

  getFileAccess(fileSpec: FileSpec): Observable<{}> {
    const vfsPath = toVFSPath(fileSpec.pathType, fileSpec.path, {
      urlEncode: true,
    });
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_403, false)
      .set(TRACK_LOADING_STATE, true);
    return this.http.head<{}>(
      `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-details${vfsPath}`,
      {context},
    );
  }

  getFileDetails(
    fileSpec: FileSpec,
    opts?: {timestamp?: Date},
  ): Observable<apiInterfaces.ApiGetFileDetailsResult> {
    const params = objectToHttpParams({
      'timestamp': opts?.timestamp?.getDate(),
    });
    const vfsPath = toVFSPath(fileSpec.pathType, fileSpec.path, {
      urlEncode: true,
    });
    return this.http.get<apiInterfaces.ApiGetFileDetailsResult>(
      `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-details${vfsPath}`,
      {
        params,
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(TRACK_LOADING_STATE, true),
      },
    );
  }

  getFileText(
    fileSpec: FileSpec,
    opts?: GetFileTextOptions,
  ): Observable<apiInterfaces.ApiGetFileTextResult | null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      encoding: apiInterfaces.ApiGetFileTextArgsEncoding.UTF_8,
      offset: '0',
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    const vfsPath = toVFSPath(fileSpec.pathType, fileSpec.path, {
      urlEncode: true,
    });
    return this.http
      .get<apiInterfaces.ApiGetFileTextResult>(
        `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-text${vfsPath}`,
        {
          params: objectToHttpParams(queryArgs as HttpParamObject),
          context: new HttpContext()
            .set(SHOW_ERROR_BAR, true)
            .set(SHOW_ERROR_BAR_FOR_404, false)
            .set(TRACK_LOADING_STATE, true),
        },
      )
      .pipe(catchError(error404To(null)));
  }

  /** Queries the length of the given VFS file. */
  getFileBlobLength(
    fileSpec: FileSpec,
    opts?: GetFileBlobOptions,
  ): Observable<bigint | null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    return this.http
      .head(getFileBlobUrl(fileSpec), {
        observe: 'response',
        params: objectToHttpParams(queryArgs as HttpParamObject),
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(SHOW_ERROR_BAR_FOR_404, false)
          .set(TRACK_LOADING_STATE, true),
      })
      .pipe(
        map((response) => {
          const length = response.headers.get('content-length');
          assertNonNull(length, 'content-length header');
          return BigInt(length);
        }),
        catchError(error404To(null)),
      );
  }

  /** Queries the raw, binary contents of a VFS file. */
  getFileBlob(
    fileSpec: FileSpec,
    opts?: GetFileBlobOptions,
  ): Observable<ArrayBuffer | null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      encoding: apiInterfaces.ApiGetFileTextArgsEncoding.UTF_8,
      offset: '0',
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    return this.http
      .get(getFileBlobUrl(fileSpec), {
        responseType: 'arraybuffer',
        params: objectToHttpParams(queryArgs as HttpParamObject),
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(SHOW_ERROR_BAR_FOR_404, false)
          .set(TRACK_LOADING_STATE, true),
      })
      .pipe(catchError(error404To(null)));
  }

  browseFilesystem(
    clientId: string,
    path: string,
    opts: {includeDirectoryTree: boolean},
  ): Observable<apiInterfaces.ApiBrowseFilesystemResult> {
    path = urlEncodePathSegments(path);

    if (!path.startsWith('/')) {
      path = '/' + path;
    }

    return this.http.get<apiInterfaces.ApiBrowseFilesystemResult>(
      `${URL_PREFIX}/clients/${clientId}/filesystem${path}`,
      {
        params: objectToHttpParams({
          'include_directory_tree': opts.includeDirectoryTree,
        }),
        context: new HttpContext()
          .set(SHOW_ERROR_BAR, true)
          .set(TRACK_LOADING_STATE, true),
      },
    );
  }

  /**
   * Triggers recollection of a file and returns the new ApiFile after
   * the recollection has been finished.
   */
  updateVfsFileContent(
    fileSpec: FileSpec,
  ): Observable<apiInterfaces.ApiGetFileDetailsResult> {
    const data: apiInterfaces.ApiUpdateVfsFileContentArgs = {
      filePath: toVFSPath(fileSpec.pathType, fileSpec.path, {urlEncode: false}),
    };
    return this.http
      .post<apiInterfaces.ApiUpdateVfsFileContentResult>(
        `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-update`,
        data,
        {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
      )
      .pipe(
        switchMap((response) =>
          this.pollVfsFileContentUpdateState(
            fileSpec.clientId,
            response.operationId!,
          ),
        ),
        takeLast(1),
        switchMap(() => this.getFileDetails(fileSpec)),
      );
  }

  private getVfsFileContentUpdateState(
    clientId: string,
    operationId: string,
  ): Observable<apiInterfaces.ApiGetVfsFileContentUpdateStateResult> {
    return this.http.get<apiInterfaces.ApiGetVfsFileContentUpdateStateResult>(
      `${URL_PREFIX}/clients/${clientId}/vfs-update/${operationId}`,
      {context: new HttpContext().set(SHOW_ERROR_BAR, true)},
    );
  }

  private pollVfsFileContentUpdateState(
    clientId: string,
    operationId: string,
  ): Observable<apiInterfaces.ApiGetVfsFileContentUpdateStateResult> {
    return timer(0, DEFAULT_POLLING_INTERVAL).pipe(
      switchMap(() => this.getVfsFileContentUpdateState(clientId, operationId)),
      takeWhile(
        (response) =>
          response.state ===
          apiInterfaces.ApiGetVfsFileContentUpdateStateResultState.RUNNING,
        true,
      ),
    );
  }

  /**
   * Triggers refresh of a VFS directory listing and returns the new listing
   * after the recollection has been finished.
   */
  refreshVfsFolder(
    fileSpec: FileSpec,
    opts?: apiInterfaces.ApiCreateVfsRefreshOperationArgs,
  ): Observable<apiInterfaces.ApiBrowseFilesystemResult> {
    const data: apiInterfaces.ApiCreateVfsRefreshOperationArgs = {
      filePath: toVFSPath(fileSpec.pathType, fileSpec.path, {urlEncode: false}),
      ...opts,
    };
    return this.http
      .post<apiInterfaces.ApiCreateVfsRefreshOperationResult>(
        `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-refresh-operations`,
        data,
      )
      .pipe(
        switchMap((response) =>
          this.pollVfsRefreshOperationState(
            fileSpec.clientId,
            response.operationId!,
          ),
        ),
        takeLast(1),
        switchMap(() =>
          this.browseFilesystem(fileSpec.clientId, fileSpec.path, {
            includeDirectoryTree: false,
          }),
        ),
      );
  }

  private getVfsRefreshOperationState(
    clientId: string,
    operationId: string,
  ): Observable<apiInterfaces.ApiGetVfsRefreshOperationStateResult> {
    return this.http.get<apiInterfaces.ApiGetVfsRefreshOperationStateResult>(
      `${URL_PREFIX}/clients/${clientId}/vfs-refresh-operations/${operationId}`,
    );
  }

  private pollVfsRefreshOperationState(
    clientId: string,
    operationId: string,
  ): Observable<apiInterfaces.ApiGetVfsRefreshOperationStateResult> {
    return timer(0, DEFAULT_POLLING_INTERVAL).pipe(
      switchMap(() => this.getVfsRefreshOperationState(clientId, operationId)),
      takeWhile(
        (response) =>
          response.state ===
          apiInterfaces.ApiGetVfsRefreshOperationStateResultState.RUNNING,
        true,
      ),
    );
  }

  listBinaries(
    includeMetadata: boolean,
  ): Observable<apiInterfaces.ApiListGrrBinariesResult> {
    return this.http
      .get<apiInterfaces.ApiListGrrBinariesResult>(
        `${URL_PREFIX}/config/binaries`,
        {
          params: objectToHttpParams({
            'include_metadata': includeMetadata,
          }),
        },
      )
      .pipe(shareReplay(1));
  }
}

const VFS_PATH_PREFIXES: {[key in apiInterfaces.PathSpecPathType]: string} = {
  [apiInterfaces.PathSpecPathType.UNSET]: '',
  [apiInterfaces.PathSpecPathType.NTFS]: 'fs/ntfs',
  [apiInterfaces.PathSpecPathType.OS]: 'fs/os',
  [apiInterfaces.PathSpecPathType.REGISTRY]: 'registry',
  [apiInterfaces.PathSpecPathType.TMPFILE]: 'temp',
  [apiInterfaces.PathSpecPathType.TSK]: 'fs/tsk',
} as const;

function toVFSPath(
  pathType: apiInterfaces.PathSpecPathType,
  path: string,
  args: {urlEncode: boolean},
): string {
  if (args?.urlEncode) {
    path = urlEncodePathSegments(path);
  }

  // Prefix Windows paths ("C:/foo") with a slash to normalize it.
  if (!path.startsWith('/')) {
    path = '/' + path;
  }

  return '/' + VFS_PATH_PREFIXES[pathType] + path;
}

function urlEncodePathSegments(path: string): string {
  // Encode backslashes, question marks and other characters that break URLs.
  return path.split('/').map(encodeURIComponent).join('/');
}

interface HttpParamObject {
  [key: string]: string | number | boolean | undefined | null;
}

function objectToHttpParams(obj: HttpParamObject): HttpParams {
  let httpParams = new HttpParams();
  for (const [key, value] of Object.entries(obj)) {
    if (value != null) {
      httpParams = httpParams.set(key, value.toString());
    }
  }
  return httpParams;
}

function findFlowDescriptor(
  flowName: string,
): (
  fds: readonly apiInterfaces.ApiFlowDescriptor[],
) => apiInterfaces.ApiFlowDescriptor {
  return (fds) => {
    const fd = fds.find((fd) => fd.name === flowName);
    if (!fd) throw new Error(`FlowDescriptors do not contain ${flowName}.`);
    return fd;
  };
}

/** Gets the URL to download all client files in the archive. */
export function getClientArchiveURL(clientId: string) {
  return `${URL_PREFIX}/clients/${clientId}/vfs-files-archive/`;
}

/** Gets the URL to download file results in TAR format for a hunt. */
export function getHuntFilesArchiveTarGzUrl(huntId: string) {
  return `${URL_PREFIX}/hunts/${huntId}/results/files-archive?archive_format=TAR_GZ`;
}

/** Gets the URL to download file results in ZIP format for a hunt. */
export function getHuntFilesArchiveZipUrl(huntId: string) {
  return `${URL_PREFIX}/hunts/${huntId}/results/files-archive?archive_format=ZIP`;
}

/** Gets the URL to download results converted to CSV. */
export function getHuntExportedResultsCsvUrl(huntId: string) {
  return `${URL_PREFIX}/hunts/${huntId}/exported-results/csv-zip`;
}

/** Gets the URL to download results converted to YAML. */
export function getHuntExportedResultsYamlUrl(huntId: string) {
  return `${URL_PREFIX}/hunts/${huntId}/exported-results/flattened-yaml-zip`;
}

/** Gets the URL to download results converted to SQLite. */
export function getHuntExportedResultsSqliteUrl(huntId: string) {
  return `${URL_PREFIX}/hunts/${huntId}/exported-results/sqlite-zip`;
}

/** Gets the URL to download file results for a flow. */
export function getFlowFilesArchiveUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/results/files-archive`;
}

/** Gets the URL to download results converted to CSV. */
export function getExportedResultsCsvUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/exported-results/csv-zip`;
}

/** Gets the URL to download results converted to YAML. */
export function getExportedResultsYamlUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/exported-results/flattened-yaml-zip`;
}

/** Gets the URL to download results converted to SQLite. */
export function getExportedResultsSqliteUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/exported-results/sqlite-zip`;
}

/** Gets the Command link to download results using the CLI. */
export function getExportedResultsCommandLink(
  prefix: string,
  clientId: string,
  filename: string,
  flowId: string,
) {
  return `${prefix} --exec_code 'grrapi.Client("${clientId}").Flow("${flowId}").GetFilesArchive().WriteToFile("${filename}")'`;
}

/** Gets the command to download hunt results using the CLI. */
export function getHuntExportCLICommand(prefix: string, huntId: string) {
  return `${prefix} --exec_code 'grrapi.Hunt("${huntId}").GetFilesArchive().WriteToFile("./hunt_results_${huntId}.zip")'`;
}

/** Returns the URL to download the raw VFS file contents. */
export function getFileBlobUrl(fileSpec: FileSpec) {
  const vfsPath = toVFSPath(fileSpec.pathType, fileSpec.path, {
    urlEncode: true,
  });
  return `${URL_PREFIX}/clients/${fileSpec.clientId}/vfs-blob${vfsPath}`;
}

/** Returns the URL to download the raw VFS temp file contents. */
export function getTempBlobUrl(clientId: string, path: string) {
  return `${URL_PREFIX}/clients/${clientId}/vfs-blob/temp/${path}`;
}

/** Returns the URL to download the Timeline flow's collected BODY file. */
export function getTimelineBodyFileUrl(
  clientId: string,
  flowId: string,
  opts: {
    timestampSubsecondPrecision: boolean;
    inodeNtfsFileReferenceFormat: boolean;
    backslashEscape: boolean;
    carriageReturnEscape: boolean;
    nonPrintableEscape: boolean;
  },
) {
  const BODY = 1;

  const url = new URL(
    `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/timeline/${BODY}`,
    document.location.origin,
  );
  url.searchParams.set(
    'body_opts.timestamp_subsecond_precision',
    Number(opts.timestampSubsecondPrecision).toString(),
  );
  url.searchParams.set(
    'body_opts.inode_ntfs_file_reference_format',
    Number(opts.inodeNtfsFileReferenceFormat).toString(),
  );
  url.searchParams.set(
    'body_opts.backslash_escape',
    Number(opts.backslashEscape).toString(),
  );
  url.searchParams.set(
    'body_opts.carriage_return_escape',
    Number(opts.carriageReturnEscape).toString(),
  );
  url.searchParams.set(
    'body_opts.non_printable_escape',
    Number(opts.nonPrintableEscape).toString(),
  );

  return url.toString();
}
