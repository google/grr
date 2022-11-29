import {HttpClient, HttpErrorResponse, HttpEvent, HttpHandler, HttpInterceptor, HttpParams, HttpParamsOptions, HttpRequest} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {merge, Observable, of, Subject, throwError, timer} from 'rxjs';
import {catchError, exhaustMap, map, mapTo, shareReplay, switchMap, take, takeLast, takeWhile, tap} from 'rxjs/operators';

import {SnackBarErrorHandler} from '../../components/helpers/error_snackbar/error_handler';
import {ApprovalConfig, ApprovalRequest} from '../../lib/models/client';
import {FlowWithDescriptor} from '../../lib/models/flow';
import {HuntApprovalKey, SafetyLimits} from '../../lib/models/hunt';
import {assertNonNull, isNonNull} from '../preconditions';

import * as apiInterfaces from './api_interfaces';

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
  readonly results: ReadonlyArray<apiInterfaces.ApiFlowResult>;
}

/**
 * Common prefix for all API calls.
 */
export const URL_PREFIX = '/api/v2';

interface ClientApprovalKey {
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


/** Interceptor that enables the sending of cookies for all HTTP requests. */
@Injectable()
export class WithCredentialsInterceptor implements HttpInterceptor {
  intercept<T>(req: HttpRequest<T>, next: HttpHandler):
      Observable<HttpEvent<T>> {
    return next.handle(req.clone(
        {withCredentials: true, setHeaders: {'X-User-Agent': 'GRR-UI/2.0'}}));
  }
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
  [key: string]: null|undefined|number|bigint|boolean|string|Date;
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
             err.status === 404 ? of(replacement) : throwError(err);
}

/**
 * Service to make HTTP requests to GRR API endpoint.
 */
@Injectable()
export class HttpApiService {
  readonly POLLING_INTERVAL = 5000;

  private readonly showErrors = {
    error: (response: HttpErrorResponse) => {
      const error = response.error;
      const address = response.url ?? 'unknown';
      let message = '';

      if (error instanceof ProgressEvent) {
        message = `Cannot reach ${address}`;
      } else if (response.headers.get('content-type')
                     ?.startsWith('text/html')) {
        // During auth problems, proxies might render fully-fledged HTML pages,
        // ignoring the fact that our request accepts JSON only. Showing the raw
        // HTML document provides no value to the user, thus we only show the
        // HTTP status code.
        message = `Received status ${response.status} ${
            response.statusText} from ${address}`;
      } else {
        message = `${error['message'] ?? error} (from ${address})`;
      }

      this.errorHandler.handleError(message);
    },
  };

  private readonly triggerApprovalPoll$ = new Subject<void>();
  private readonly triggerListScheduledFlowsPoll$ = new Subject<void>();
  private readonly triggerListFlowsPoll$ = new Subject<void>();

  constructor(
      private readonly http: HttpClient,
      private readonly errorHandler: SnackBarErrorHandler) {}

  /**
   * Searches for clients using given API arguments.
   */
  searchClients(args: apiInterfaces.ApiSearchClientsArgs):
      Observable<apiInterfaces.ApiSearchClientsResult> {
    let params = new HttpParams().set('query', args.query || '');
    if (args.offset) {
      params = params.set('offset', args.offset.toString());
    }
    if (args.count) {
      params = params.set('count', args.count.toString());
    }

    return this.http.get<apiInterfaces.ApiSearchClientsResult>(
        `${URL_PREFIX}/clients`, {params});
  }

  private fetchClient(id: string): Observable<apiInterfaces.ApiClient> {
    return this.http.get<apiInterfaces.ApiClient>(`${URL_PREFIX}/clients/${id}`)
        .pipe(tap(this.showErrors));
  }

  /** Fetches a client by its ID. */
  subscribeToClient(clientId: string): Observable<apiInterfaces.ApiClient> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchClient(clientId)),
            tap(this.showErrors),
        );
  }

  /** Requests approval to give the current user access to a client. */
  requestApproval(args: ApprovalRequest):
      Observable<apiInterfaces.ApiClientApproval> {
    const request: apiInterfaces.ApiCreateClientApprovalArgs = {
      approval: {
        reason: args.reason,
        notifiedUsers: args.approvers,
        emailCcAddresses: args.cc,
      },
    };

    return this.http
        .post<apiInterfaces.ApiClientApproval>(
            `${URL_PREFIX}/users/me/approvals/client/${args.clientId}`, request)
        .pipe(
            tap(() => {
              this.triggerApprovalPoll$.next();
            }),
        );
  }

  fetchApprovalConfig(): Observable<ApprovalConfig> {
    return this.http
        .get<apiInterfaces.ApiConfigOption>(
            `${URL_PREFIX}/config/Email.approval_optional_cc_address`)
        .pipe(
            // Replace empty string (protobuf default) with undefined.
            map(res => res.value?.['value'] as string ?? undefined),
            map(optionalCcEmail => ({optionalCcEmail})),
            tap(this.showErrors),
        );
  }

  /** Lists ClientApprovals in reversed chronological order. */
  private listApprovals(clientId: string):
      Observable<ReadonlyArray<apiInterfaces.ApiClientApproval>> {
    return this.http
        .get<apiInterfaces.ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client/${clientId}`)
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  subscribeToListApprovals(clientId: string) {
    return merge(timer(0, this.POLLING_INTERVAL), this.triggerApprovalPoll$)
        .pipe(
            exhaustMap(() => this.listApprovals(clientId)),
            tap(this.showErrors),
        );
  }

  private verifyClientAccess(clientId: string): Observable<boolean> {
    return this.http.get<{}>(`${URL_PREFIX}/clients/${clientId}/access`)
        .pipe(
            map(() => true),
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return of(false);
              } else {
                return throwError(err);
              }
            }),
            tap(this.showErrors),
        );
  }

  /** Emits true, if the user has access to the client, false otherwise. */
  subscribeToVerifyClientAccess(clientId: string): Observable<boolean> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.verifyClientAccess(clientId)),
            tap(this.showErrors),
        );
  }

  /** Fetches a ClientApproval. */
  private fetchClientApproval({clientId, requestor, approvalId}:
                                  ClientApprovalKey):
      Observable<apiInterfaces.ApiClientApproval> {
    return this.http
        .get<apiInterfaces.ApiClientApproval>(`${URL_PREFIX}/users/${
            requestor}/approvals/client/${clientId}/${approvalId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  /** Fetches a Flow. */
  fetchFlow(clientId: string, flowId: string):
      Observable<apiInterfaces.ApiFlow> {
    return this.http
        .get<apiInterfaces.ApiFlow>(
            `${URL_PREFIX}/clients/${clientId}/flows/${flowId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  createHunt(
      description: string, flowWithDescriptors: FlowWithDescriptor,
      safetyLimits: SafetyLimits, rules: apiInterfaces.ForemanClientRuleSet,
      outputPlugins: ReadonlyArray<apiInterfaces.OutputPluginDescriptor>):
      Observable<apiInterfaces.ApiHunt> {
    const huntRunnerArgs: apiInterfaces.HuntRunnerArgs = {
      description,
      cpuLimit: safetyLimits.cpuLimit?.toString(),
      networkBytesLimit: safetyLimits.networkBytesLimit?.toString(),
      clientRate: safetyLimits.clientRate,
      crashLimit: safetyLimits.crashLimit?.toString(),
      avgResultsPerClientLimit:
          safetyLimits.avgResultsPerClientLimit?.toString(),
      avgCpuSecondsPerClientLimit:
          safetyLimits.avgCpuSecondsPerClientLimit?.toString(),
      avgNetworkBytesPerClientLimit:
          safetyLimits.avgNetworkBytesPerClientLimit?.toString(),
      expiryTime: safetyLimits.expiryTime?.toString(),
      clientLimit: safetyLimits.clientLimit?.toString(),
      outputPlugins,
      clientRuleSet: rules,
    };
    const originalFlow: apiInterfaces.ApiFlowReference = {
      flowId: flowWithDescriptors.flow.flowId,
      clientId: flowWithDescriptors.flow.clientId,
    };
    const request: apiInterfaces.ApiCreateHuntArgs = {
      flowName: flowWithDescriptors.flow.name,
      flowArgs: {
        '@type': flowWithDescriptors.flowArgType,
        ...(flowWithDescriptors.flow.args as {}),
      },
      huntRunnerArgs,
      originalFlow,
    };
    return this.http.post<apiInterfaces.ApiHunt>(
        `${URL_PREFIX}/hunts`, toJson(request));
  }

  requestHuntApproval(
      huntId: string, approvalArgs: apiInterfaces.ApiHuntApproval):
      Observable<apiInterfaces.ApiHuntApproval> {
    const request: apiInterfaces.ApiCreateHuntApprovalArgs = {
      huntId,
      approval: approvalArgs,
    };
    return this.http.post<apiInterfaces.ApiHuntApproval>(
        `${URL_PREFIX}/users/me/approvals/hunt/${huntId}`, request);
  }

  private fetchHunt(id: string): Observable<apiInterfaces.ApiHunt> {
    return this.http.get<apiInterfaces.ApiHunt>(`${URL_PREFIX}/hunts/${id}`)
        .pipe(tap(this.showErrors));
  }

  subscribeToHuntApproval(key: HuntApprovalKey):
      Observable<apiInterfaces.ApiHuntApproval> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchHuntApproval(key)),
            tap(this.showErrors),
        );
  }

  /** Fetches a HuntApproval */
  private fetchHuntApproval({huntId, approvalId, requestor}: HuntApprovalKey):
      Observable<apiInterfaces.ApiHuntApproval> {
    return this.http
        .get<apiInterfaces.ApiHuntApproval>(`${URL_PREFIX}/users/${
            requestor}/approvals/hunt/${huntId}/${approvalId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  /** Grants a HuntApproval. */
  grantHuntApproval({huntId, approvalId, requestor}: HuntApprovalKey):
      Observable<apiInterfaces.ApiHuntApproval> {
    return this.http.post<apiInterfaces.ApiHuntApproval>(
        `${URL_PREFIX}/users/${requestor}/approvals/hunt/${huntId}/${
            approvalId}/actions/grant`,
        {});
  }

  subscribeToHunt(huntId: string): Observable<apiInterfaces.ApiHunt> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchHunt(huntId)),
            tap(this.showErrors),
        );
  }

  patchHunt(huntId: string, patch: {state: apiInterfaces.ApiHuntState}):
      Observable<apiInterfaces.ApiHunt> {
    const params: apiInterfaces.ApiModifyHuntArgs = {...patch};
    return this.http
        .patch<apiInterfaces.ApiHunt>(`${URL_PREFIX}/hunts/${huntId}`, params)
        .pipe(tap(this.showErrors));
  }

  /** Lists results of the given hunt. */
  listResultsForHunt(params: apiInterfaces.ApiListHuntResultsArgs):
      Observable<ReadonlyArray<apiInterfaces.ApiHuntResult>> {
    const huntId = params.huntId;
    assertNonNull(huntId);

    const options: {[key: string]: number|string} = {};
    if (params.count) {
      options['count'] = params.count;
    }

    const httpParams = new HttpParams({
      fromObject: {
        'huntId': huntId,
        ...options,
      }
    });

    return this.http
        .get<apiInterfaces.ApiListHuntResultsResult>(
            `${URL_PREFIX}/hunts/${params.huntId}/results`,
            {params: httpParams})
        .pipe(
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return throwError(new MissingApprovalError(err));
              } else {
                return throwError(err);
              }
            }),
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  subscribeToResultsForHunt(params: apiInterfaces.ApiListHuntResultsArgs):
      Observable<ReadonlyArray<apiInterfaces.ApiHuntResult>> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listResultsForHunt(params)),
            tap(this.showErrors),
        );
  }

  /** Lists errors of the given hunt. */
  listErrorsForHunt(params: apiInterfaces.ApiListHuntErrorsArgs):
      Observable<readonly apiInterfaces.ApiHuntError[]> {
    const huntId = params.huntId;
    assertNonNull(huntId);

    const options: {[key: string]: number|string} = {};
    if (params.count) {
      options['count'] = params.count;
    }

    const httpParams = new HttpParams({
      fromObject: {
        'huntId': huntId,
        ...options,
      }
    });

    return this.http
        .get<apiInterfaces.ApiListHuntErrorsResult>(
            `${URL_PREFIX}/hunts/${params.huntId}/errors`, {params: httpParams})
        .pipe(
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return throwError(new MissingApprovalError(err));
              } else {
                return throwError(err);
              }
            }),
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  subscribeToErrorsForHunt(params: apiInterfaces.ApiListHuntErrorsArgs):
      Observable<readonly apiInterfaces.ApiHuntError[]> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listErrorsForHunt(params)),
            tap(this.showErrors),
        );
  }

  // TODO: GET parameters require snake_case not camelCase
  // parameters. Do not allow createdBy and other camelCase parameters until
  // fixed.
  private listHunts(args:
                        Pick<apiInterfaces.ApiListHuntsArgs, 'offset'|'count'>):
      Observable<apiInterfaces.ApiListHuntsResult> {
    const params = toHttpParams(args).append('with_full_summary', true);
    return this.http
        .get<apiInterfaces.ApiListHuntsResult>(`${URL_PREFIX}/hunts`, {params})
        .pipe(tap(this.showErrors));
  }

  subscribeToListHunts(
      args: Pick<apiInterfaces.ApiListHuntsArgs, 'offset'|'count'>):
      Observable<apiInterfaces.ApiListHuntsResult> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listHunts(args)),
        );
  }

  subscribeToClientApproval(key: ClientApprovalKey):
      Observable<apiInterfaces.ApiClientApproval> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchClientApproval(key)),
            tap(this.showErrors),
        );
  }


  /** Grants a ClientApproval. */
  grantClientApproval({clientId, requestor, approvalId}: ClientApprovalKey):
      Observable<apiInterfaces.ApiClientApproval> {
    return this.http.post<apiInterfaces.ApiClientApproval>(
        `${URL_PREFIX}/users/${requestor}/approvals/client/${clientId}/${
            approvalId}/actions/grant`,
        {});
  }

  private readonly flowDescriptors$ =
      this.http
          .get<apiInterfaces.ApiListFlowDescriptorsResult>(
              `${URL_PREFIX}/flows/descriptors`)
          .pipe(
              map(res => res.items ?? []),
              tap(this.showErrors),
              shareReplay(1),  // Cache latest FlowDescriptors.
          );

  listFlowDescriptors():
      Observable<ReadonlyArray<apiInterfaces.ApiFlowDescriptor>> {
    return this.flowDescriptors$;
  }

  listArtifactDescriptors():
      Observable<ReadonlyArray<apiInterfaces.ArtifactDescriptor>> {
    return this.http
        .get<apiInterfaces.ApiListArtifactsResult>(`${URL_PREFIX}/artifacts`)
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  listOutputPluginDescriptors():
      Observable<readonly apiInterfaces.ApiOutputPluginDescriptor[]> {
    return this.http
        .get<apiInterfaces.ApiListOutputPluginDescriptorsResult>(
            `${URL_PREFIX}/output-plugins/all`)
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
            shareReplay({bufferSize: 1, refCount: true}),
        );
  }

  private listFlowsForClient(args: apiInterfaces.ApiListFlowsArgs):
      Observable<ReadonlyArray<apiInterfaces.ApiFlow>> {
    const clientId = args.clientId;
    assertNonNull(clientId);

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
            `${URL_PREFIX}/clients/${clientId}/flows`, {params})
        .pipe(
            catchError((err: HttpErrorResponse) => {
              if (err.status === 403) {
                return throwError(new MissingApprovalError(err));
              } else {
                return throwError(err);
              }
            }),
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  /** Lists the latest Flows for the given Client. */
  subscribeToFlowsForClient(args: apiInterfaces.ApiListFlowsArgs):
      Observable<ReadonlyArray<apiInterfaces.ApiFlow>> {
    return merge(timer(0, this.POLLING_INTERVAL), this.triggerListFlowsPoll$)
        .pipe(
            exhaustMap(() => this.listFlowsForClient(args)),
            tap(this.showErrors),
        );
  }

  subscribeToScheduledFlowsForClient(clientId: string, creator: string):
      Observable<ReadonlyArray<apiInterfaces.ApiScheduledFlow>> {
    return merge(
               timer(0, this.POLLING_INTERVAL),
               this.triggerListScheduledFlowsPoll$)
        .pipe(
            exhaustMap(() => this.listScheduledFlows(clientId, creator)),
            tap(this.showErrors),
        );
  }


  /** Lists all scheduled flows for the given client and user. */
  private listScheduledFlows(clientId: string, creator: string):
      Observable<ReadonlyArray<apiInterfaces.ApiScheduledFlow>> {
    return this.http
        .get<apiInterfaces.ApiListScheduledFlowsResult>(
            // TODO: Remove trailing slash once redirect protocol
            // is fixed.
            `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${creator}/`)
        .pipe(
            map(res => res.scheduledFlows ?? []),
            tap(this.showErrors),
        );
  }


  /** Lists results of the given flow. */
  listResultsForFlow(params: FlowResultsParams):
      Observable<ReadonlyArray<apiInterfaces.ApiFlowResult>> {
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
      }
    });

    return this.http
        .get<apiInterfaces.ApiListFlowResultsResult>(
            `${URL_PREFIX}/clients/${params.clientId}/flows/${
                params.flowId}/results`,
            {params: httpParams})
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  /** Continuously lists results for the given flow, e.g. by polling. */
  subscribeToResultsForFlow(params: FlowResultsParams):
      Observable<ReadonlyArray<apiInterfaces.ApiFlowResult>> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listResultsForFlow(params)),
            tap(this.showErrors),
        );
  }

  /** Starts a Flow on the given Client. */
  startFlow(clientId: string, flowName: string, flowArgs: apiInterfaces.Any):
      Observable<apiInterfaces.ApiFlow> {
    return this.listFlowDescriptors().pipe(
        // Take FlowDescriptors at most once, so that Flows are not started
        // repeatedly if FlowDescriptors are ever updated.
        take(1),
        map(findFlowDescriptor(flowName)),
        map(fd => ({
              clientId,
              flow: {
                name: flowName,
                args: {
                  '@type': fd.defaultArgs?.['@type'],
                  ...flowArgs,
                },
              }
            })),
        switchMap((request: apiInterfaces.ApiCreateFlowArgs) => {
          return this.http
              .post<apiInterfaces.ApiFlow>(
                  `${URL_PREFIX}/clients/${clientId}/flows`, request)
              .pipe(
                  tap(() => {
                    this.triggerListFlowsPoll$.next();
                  }),
                  tap(this.showErrors),
                  catchError(
                      (e: HttpErrorResponse) =>
                          throwError(new Error(e.error.message ?? e.message))),
              );
        }),
    );
  }

  /** Schedules a Flow on the given Client. */
  scheduleFlow(clientId: string, flowName: string, flowArgs: apiInterfaces.Any):
      Observable<apiInterfaces.ApiScheduledFlow> {
    return this.listFlowDescriptors().pipe(
        // Take FlowDescriptors at most once, so that Flows are not scheduled
        // repeatedly if FlowDescriptors are ever updated.
        take(1),
        map(findFlowDescriptor(flowName)),
        map(fd => ({
              clientId,
              flow: {
                name: flowName,
                args: {
                  '@type': fd.defaultArgs?.['@type'],
                  ...flowArgs,
                },
              }
            })),
        switchMap((request: apiInterfaces.ApiCreateFlowArgs) => {
          return this.http
              .post<apiInterfaces.ApiFlow>(
                  `${URL_PREFIX}/clients/${clientId}/scheduled-flows`, request)
              .pipe(
                  tap(() => {
                    this.triggerListScheduledFlowsPoll$.next();
                  }),
                  tap(this.showErrors),
                  catchError(
                      (e: HttpErrorResponse) =>
                          throwError(new Error(e.error.message ?? e.message))),
              );
        }),
    );
  }

  /** Cancels the given Flow. */
  cancelFlow(clientId: string, flowId: string):
      Observable<apiInterfaces.ApiFlow> {
    const url =
        `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/actions/cancel`;
    return this.http.post<apiInterfaces.ApiFlow>(url, {}).pipe(
        tap(() => {
          this.triggerListFlowsPoll$.next();
        }),
        tap(this.showErrors),
    );
  }

  /** Unschedules a previously scheduled flow. */
  unscheduleFlow(clientId: string, scheduledFlowId: string): Observable<{}> {
    // TODO: Remove trailing slash once redirect protocol is fixed.
    const url =
        `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${scheduledFlowId}/`;
    return this.http.delete<{}>(url, {}).pipe(
        tap(() => {
          this.triggerListScheduledFlowsPoll$.next();
        }),
        tap(this.showErrors),
    );
  }

  /** Fetches the current user. */
  fetchCurrentUser(): Observable<apiInterfaces.ApiGrrUser> {
    return this.http.get<apiInterfaces.ApiGrrUser>(`${URL_PREFIX}/users/me`)
        .pipe(
            tap(this.showErrors),
        );
  }

  /** Explains a GlobExpression. */
  explainGlobExpression(
      clientId: string, globExpression: string,
      {exampleCount}: {exampleCount: number}):
      Observable<ReadonlyArray<apiInterfaces.GlobComponentExplanation>> {
    const url = `${URL_PREFIX}/clients/${clientId}/glob-expressions:explain`;
    const args: apiInterfaces.ApiExplainGlobExpressionArgs = {
      globExpression,
      exampleCount
    };
    return this.http
        .post<apiInterfaces.ApiExplainGlobExpressionResult>(url, args)
        .pipe(
            map(result => result.components ?? []),
            tap(this.showErrors),
        );
  }

  fetchUiConfig(): Observable<apiInterfaces.ApiUiConfig> {
    return this.http.get<apiInterfaces.ApiUiConfig>(`${URL_PREFIX}/config/ui`)
        .pipe(
            tap(this.showErrors),
        );
  }


  addClientLabel(clientId: string, label: string): Observable<{}> {
    const url = `${URL_PREFIX}/clients/labels/add`;
    const body: apiInterfaces.ApiAddClientsLabelsArgs = {
      clientIds: [clientId],
      labels: [label]
    };
    return this.http.post<{}>(url, body).pipe(
        tap(this.showErrors),
    );
  }

  removeClientLabel(clientId: string, label: string): Observable<string> {
    const url = `${URL_PREFIX}/clients/labels/remove`;
    const body: apiInterfaces.ApiRemoveClientsLabelsArgs = {
      clientIds: [clientId],
      labels: [label]
    };
    return this.http.post<{}>(url, body).pipe(
        mapTo(label),
        tap(this.showErrors),
        catchError(
            (e: HttpErrorResponse) =>
                throwError(new Error(e.error.message ?? e.message))),
    );
  }

  fetchAllClientsLabels():
      Observable<ReadonlyArray<apiInterfaces.ClientLabel>> {
    const url = `${URL_PREFIX}/clients/labels`;
    return this.http.get<apiInterfaces.ApiListClientsLabelsResult>(url).pipe(
        map(clientsLabels => clientsLabels.items ?? []),
        tap(this.showErrors),
    );
  }

  fetchClientVersions(clientId: string, start?: Date, end?: Date):
      Observable<ReadonlyArray<apiInterfaces.ApiClient>> {
    const url = `${URL_PREFIX}/clients/${clientId}/versions`;

    const params = new HttpParams({
      fromObject: {
        // If start not set, fetch from beginning of time
        start: ((start?.getTime() ?? 1) * 1000).toString(),
        end: ((end ?? new Date()).getTime() * 1000).toString(),
      }
    });

    return this.http
        .get<apiInterfaces.ApiGetClientVersionsResult>(url, {params})
        .pipe(
            map(clientVersions => clientVersions.items ?? []),
            tap(this.showErrors),
        );
  }

  suggestApprovers(usernameQuery: string): Observable<ReadonlyArray<
      apiInterfaces.ApiListApproverSuggestionsResultApproverSuggestion>> {
    const params = new HttpParams().set('username_query', usernameQuery);
    return this.http
        .get<apiInterfaces.ApiListApproverSuggestionsResult>(
            `${URL_PREFIX}/users/approver-suggestions`, {params})
        .pipe(
            map(result => result.suggestions ?? []),
            tap(this.showErrors),
        );
  }

  listRecentClientApprovals(parameters: {count?: number}):
      Observable<ReadonlyArray<apiInterfaces.ApiClientApproval>> {
    return this.http
        .get<apiInterfaces.ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client`,
            {params: objectToHttpParams(parameters)})
        .pipe(
            map(result => result.items ?? []),
            tap(this.showErrors),
        );
  }

  getFileDetails(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      opts?: {timestamp?: Date},
      ): Observable<apiInterfaces.ApiFile> {
    const params = objectToHttpParams({timestamp: opts?.timestamp?.getDate()});
    const vfsPath = toVFSPath(pathType, path, {urlEncode: true});
    return this.http
        .get<apiInterfaces.ApiGetFileDetailsResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-details${vfsPath}`, {params})
        .pipe(
            map(response => response.file ?? {}),
            tap(this.showErrors),
        );
  }

  getFileText(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      opts?: GetFileTextOptions,
      ): Observable<apiInterfaces.ApiGetFileTextResult|null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      encoding: apiInterfaces.ApiGetFileTextArgsEncoding.UTF_8,
      offset: '0',
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    const vfsPath = toVFSPath(pathType, path, {urlEncode: true});
    return this.http
        .get<apiInterfaces.ApiGetFileTextResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-text${vfsPath}`,
            {params: objectToHttpParams(queryArgs as HttpParamObject)})
        .pipe(
            catchError(error404To(null)),
            tap(this.showErrors),
        );
  }

  /** Queries the length of the given VFS file. */
  getFileBlobLength(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      opts?: GetFileBlobOptions,
      ): Observable<bigint|null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    return this.http
        .head(getFileBlobUrl(clientId, pathType, path), {
          observe: 'response',
          params: objectToHttpParams(queryArgs as HttpParamObject),
        })
        .pipe(
            map(response => {
              const length = response.headers.get('content-length');
              assertNonNull(length, 'content-length header');
              return BigInt(length);
            }),
            catchError(error404To(null)),
            tap(this.showErrors),
        );
  }

  /** Queries the raw, binary contents of a VFS file. */
  getFileBlob(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      opts?: GetFileBlobOptions,
      ): Observable<ArrayBuffer|null> {
    const queryArgs: apiInterfaces.ApiGetFileTextArgs = {
      encoding: apiInterfaces.ApiGetFileTextArgsEncoding.UTF_8,
      offset: '0',
      ...opts,
      timestamp: opts?.timestamp?.getTime()?.toString(),
    };

    return this.http
        .get(getFileBlobUrl(clientId, pathType, path), {
          responseType: 'arraybuffer',
          params: objectToHttpParams(queryArgs as HttpParamObject),
        })
        .pipe(
            catchError(error404To(null)),
            tap(this.showErrors),
        );
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

    return this.http
        .get<apiInterfaces.ApiBrowseFilesystemResult>(
            `${URL_PREFIX}/clients/${clientId}/filesystem${path}`, {
              params: objectToHttpParams(
                  {'include_directory_tree': opts.includeDirectoryTree}),
            })
        .pipe(
            tap(this.showErrors),
        );
  }

  /**
   * Triggers recollection of a file and returns the new ApiFile after
   * the recollection has been finished.
   */
  updateVfsFileContent(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      ): Observable<apiInterfaces.ApiFile> {
    const data: apiInterfaces.ApiUpdateVfsFileContentArgs = {
      filePath: toVFSPath(pathType, path, {urlEncode: false}),
    };
    return this.http
        .post<apiInterfaces.ApiUpdateVfsFileContentResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-update`, data)
        .pipe(
            switchMap(
                response => this.pollVfsFileContentUpdateState(
                    clientId, response.operationId!)),
            takeLast(1),
            switchMap(() => this.getFileDetails(clientId, pathType, path)),
            tap(this.showErrors),
        );
  }

  private getVfsFileContentUpdateState(
      clientId: string,
      operationId: string,
      ): Observable<apiInterfaces.ApiGetVfsFileContentUpdateStateResult> {
    return this.http
        .get<apiInterfaces.ApiGetVfsFileContentUpdateStateResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-update/${operationId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  private pollVfsFileContentUpdateState(
      clientId: string,
      operationId: string,
      ): Observable<apiInterfaces.ApiGetVfsFileContentUpdateStateResult> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            switchMap(
                () => this.getVfsFileContentUpdateState(clientId, operationId)),
            takeWhile(
                (response) => response.state ===
                    apiInterfaces.ApiGetVfsFileContentUpdateStateResultState
                        .RUNNING,
                true),
            tap(this.showErrors),
        );
  }

  /**
   * Triggers refresh of a VFS directory listing and returns the new listing
   * after the recollection has been finished.
   */
  refreshVfsFolder(
      clientId: string,
      pathType: apiInterfaces.PathSpecPathType,
      path: string,
      opts?: apiInterfaces.ApiCreateVfsRefreshOperationArgs,
      ): Observable<apiInterfaces.ApiBrowseFilesystemResult> {
    const data: apiInterfaces.ApiCreateVfsRefreshOperationArgs = {
      filePath: toVFSPath(pathType, path, {urlEncode: false}),
      ...opts,
    };
    return this.http
        .post<apiInterfaces.ApiCreateVfsRefreshOperationResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-refresh-operations`, data)
        .pipe(
            switchMap(
                response => this.pollVfsRefreshOperationState(
                    clientId, response.operationId!)),
            tap(this.showErrors),
            takeLast(1),
            switchMap(
                () => this.browseFilesystem(
                    clientId, path, {includeDirectoryTree: false})),
        );
  }

  private getVfsRefreshOperationState(
      clientId: string,
      operationId: string,
      ): Observable<apiInterfaces.ApiGetVfsRefreshOperationStateResult> {
    return this.http
        .get<apiInterfaces.ApiGetVfsRefreshOperationStateResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-refresh-operations/${
                operationId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  private pollVfsRefreshOperationState(
      clientId: string,
      operationId: string,
      ): Observable<apiInterfaces.ApiGetVfsRefreshOperationStateResult> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            switchMap(
                () => this.getVfsRefreshOperationState(clientId, operationId)),
            takeWhile(
                (response) => response.state ===
                    apiInterfaces.ApiGetVfsRefreshOperationStateResultState
                        .RUNNING,
                true),
            tap(this.showErrors),
        );
  }

  listBinaries() {
    return this.http.get<apiInterfaces.ApiListGrrBinariesResult>(
        `${URL_PREFIX}/config/binaries`);
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
    pathType: apiInterfaces.PathSpecPathType, path: string,
    args: {urlEncode: boolean}): string {
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
  [key: string]: string|number|boolean|undefined|null;
}

function objectToHttpParams(obj: HttpParamObject): HttpParams {
  let httpParams = new HttpParams();
  for (const [key, value] of Object.entries(obj)) {
    if (isNonNull(value)) {
      httpParams = httpParams.set(key, value.toString());
    }
  }
  return httpParams;
}

function findFlowDescriptor(flowName: string):
    (fds: ReadonlyArray<apiInterfaces.ApiFlowDescriptor>) =>
        apiInterfaces.ApiFlowDescriptor {
  return fds => {
    const fd = fds.find(fd => fd.name === flowName);
    if (!fd) throw new Error(`FlowDescriptors do not contain ${flowName}.`);
    return fd;
  };
}


function toJson(data: unknown) {
  return JSON.stringify(data, (k, v) => typeof v === 'bigint' ? `${v}` : v);
}

/** Gets the URL to download file results. */
export function getFlowFilesArchiveUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${
      flowId}/results/files-archive`;
}

/** Gets the URL to download results converted to CSV. */
export function getExportedResultsCsvUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${
      flowId}/exported-results/csv-zip`;
}

/** Gets the URL to download results converted to YAML. */
export function getExportedResultsYamlUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${
      flowId}/exported-results/flattened-yaml-zip`;
}

/** Gets the URL to download results converted to SQLite. */
export function getExportedResultsSqliteUrl(clientId: string, flowId: string) {
  return `${URL_PREFIX}/clients/${clientId}/flows/${
      flowId}/exported-results/sqlite-zip`;
}

/** Returns the URL to download the raw VFS file contents. */
export function getFileBlobUrl(
    clientId: string, pathType: apiInterfaces.PathSpecPathType, path: string) {
  const vfsPath = toVFSPath(pathType, path, {urlEncode: true});
  return `${URL_PREFIX}/clients/${clientId}/vfs-blob${vfsPath}`;
}

/** Returns the URL to download the raw VFS temp file contents. */
export function getTempBlobUrl(clientId: string, path: string) {
  return `${URL_PREFIX}/clients/${clientId}/vfs-blob/temp/${path}`;
}

/** Returns the URL to download the Timeline flow's collected BODY file. */
export function getTimelineBodyFileUrl(clientId: string, flowId: string, opts: {
  timestampSubsecondPrecision: boolean,
  inodeNtfsFileReferenceFormat: boolean,
  backslashEscape: boolean,
  carriageReturnEscape: boolean,
  nonPrintableEscape: boolean,
}) {
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
