import {HttpClient, HttpErrorResponse, HttpEvent, HttpHandler, HttpInterceptor, HttpParams, HttpParamsOptions, HttpRequest} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {MatSnackBar} from '@angular/material/snack-bar';
import {Observable, of, throwError, timer} from 'rxjs';
import {catchError, exhaustMap, map, mapTo, shareReplay, switchMap, take, takeLast, takeWhile, tap} from 'rxjs/operators';

import {ErrorSnackbar} from '../../components/helpers/error_snackbar/error_snackbar';
import {ApprovalConfig, ApprovalRequest} from '../../lib/models/client';
import {FlowWithDescriptor} from '../../lib/models/flow';
import {SafetyLimits} from '../../lib/models/hunt';
import {assertNonNull, isNonNull} from '../preconditions';

import {AnyObject, ApiAddClientsLabelsArgs, ApiApprovalOptionalCcAddressResult, ApiClient, ApiClientApproval, ApiClientLabel, ApiCreateClientApprovalArgs, ApiCreateFlowArgs, ApiCreateHuntApprovalArgs, ApiCreateHuntArgs, ApiCreateVfsRefreshOperationArgs, ApiCreateVfsRefreshOperationResult, ApiExplainGlobExpressionArgs, ApiExplainGlobExpressionResult, ApiFile, ApiFlow, ApiFlowDescriptor, ApiFlowReference, ApiFlowResult, ApiGetClientVersionsResult, ApiGetFileDetailsResult, ApiGetFileTextArgs, ApiGetFileTextArgsEncoding, ApiGetFileTextResult, ApiGetVfsFileContentUpdateStateResult, ApiGetVfsFileContentUpdateStateResultState, ApiGetVfsRefreshOperationStateResult, ApiGetVfsRefreshOperationStateResultState, ApiGrrUser, ApiHunt, ApiHuntApproval, ApiListApproverSuggestionsResult, ApiListArtifactsResult, ApiListClientApprovalsResult, ApiListClientFlowDescriptorsResult, ApiListClientsLabelsResult, ApiListFilesArgs, ApiListFilesResult, ApiListFlowResultsResult, ApiListFlowsArgs, ApiListFlowsResult, ApiListGrrBinariesResult, ApiListScheduledFlowsResult, ApiRemoveClientsLabelsArgs, ApiScheduledFlow, ApiSearchClientResult, ApiSearchClientsArgs, ApiUiConfig, ApiUpdateVfsFileContentArgs, ApiUpdateVfsFileContentResult, ApproverSuggestion, ArtifactDescriptor, DecimalString, ForemanClientRuleSet, GlobComponentExplanation, HuntRunnerArgs, PathSpecPathType} from './api_interfaces';


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
  readonly results: ReadonlyArray<ApiFlowResult>;
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
  readonly offset?: DecimalString;
  readonly length?: DecimalString;
  readonly timestamp?: Date;
  readonly encoding?: ApiGetFileTextArgsEncoding;
}

/** Arguments of GetFileBlob API call. */
export interface GetFileBlobOptions {
  readonly offset?: DecimalString;
  readonly length?: DecimalString;
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

      this.snackBar.openFromComponent(ErrorSnackbar, {data: message});
    },
  };

  constructor(
      private readonly http: HttpClient,
      private readonly snackBar: MatSnackBar) {}

  /**
   * Searches for clients using given API arguments.
   */
  searchClients(args: ApiSearchClientsArgs): Observable<ApiSearchClientResult> {
    const params = new HttpParams().set('query', args.query || '');
    if (args.offset) {
      params.set('offset', args.offset.toString());
    }
    if (args.count) {
      params.set('count', args.count.toString());
    }

    return this.http.get<ApiSearchClientResult>(
        `${URL_PREFIX}/clients`, {params});
  }

  private fetchClient(id: string): Observable<ApiClient> {
    return this.http.get<ApiClient>(`${URL_PREFIX}/clients/${id}`)
        .pipe(tap(this.showErrors));
  }

  /** Fetches a client by its ID. */
  subscribeToClient(clientId: string): Observable<ApiClient> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchClient(clientId)),
            tap(this.showErrors),
        );
  }

  /** Requests approval to give the current user access to a client. */
  requestApproval(args: ApprovalRequest): Observable<ApiClientApproval> {
    const request: ApiCreateClientApprovalArgs = {
      approval: {
        reason: args.reason,
        notifiedUsers: args.approvers,
        emailCcAddresses: args.cc,
      },
    };

    return this.http.post<ApiClientApproval>(
        `${URL_PREFIX}/users/me/approvals/client/${args.clientId}`, request);
  }

  fetchApprovalConfig(): Observable<ApprovalConfig> {
    return this.http
        .get<ApiApprovalOptionalCcAddressResult>(
            `${URL_PREFIX}/config/Email.approval_optional_cc_address`)
        .pipe(
            // Replace empty string (protobuf default) with undefined.
            map(res => (res.value || {}).value || undefined),
            map(optionalCcEmail => ({optionalCcEmail})),
            tap(this.showErrors),
        );
  }

  /** Lists ClientApprovals in reversed chronological order. */
  private listApprovals(clientId: string):
      Observable<ReadonlyArray<ApiClientApproval>> {
    return this.http
        .get<ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client/${clientId}`)
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  subscribeToListApprovals(clientId: string) {
    return timer(0, this.POLLING_INTERVAL)
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
      Observable<ApiClientApproval> {
    return this.http
        .get<ApiClientApproval>(`${URL_PREFIX}/users/${
            requestor}/approvals/client/${clientId}/${approvalId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  /** Fetches a Flow. */
  fetchFlow(clientId: string, flowId: string): Observable<ApiFlow> {
    return this.http
        .get<ApiFlow>(`${URL_PREFIX}/clients/${clientId}/flows/${flowId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  createHunt(
      description: string, flowWithDescriptors: FlowWithDescriptor,
      safetyLimits: SafetyLimits,
      rules: ForemanClientRuleSet): Observable<ApiHunt> {
    const huntRunnerArgs: HuntRunnerArgs = {
      description,
      ...safetyLimits,
      clientRuleSet: rules,
    };
    const originalFlow: ApiFlowReference = {
      flowId: flowWithDescriptors.flow.flowId,
      clientId: flowWithDescriptors.flow.clientId,
    };
    const args = flowWithDescriptors.flow.args as AnyObject;
    const request: ApiCreateHuntArgs = {
      flowName: flowWithDescriptors.flow.name,
      flowArgs: {
        '@type': flowWithDescriptors.flowArgType,
        ...args,
      },
      huntRunnerArgs,
      originalFlow,
    };
    return this.http.post<ApiHunt>(`${URL_PREFIX}/hunts`, toJson(request));
  }

  requestHuntApproval(huntId: string, approvalArgs: ApiHuntApproval):
      Observable<ApiHuntApproval> {
    const request: ApiCreateHuntApprovalArgs = {
      huntId,
      approval: approvalArgs,
    };
    return this.http.post<ApiHuntApproval>(
        `${URL_PREFIX}/users/me/approvals/hunt/${huntId}`, request);
  }

  subscribeToClientApproval(key: ClientApprovalKey):
      Observable<ApiClientApproval> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.fetchClientApproval(key)),
            tap(this.showErrors),
        );
  }


  /** Grants a ClientApproval. */
  grantClientApproval({clientId, requestor, approvalId}: ClientApprovalKey):
      Observable<ApiClientApproval> {
    return this.http.post<ApiClientApproval>(
        `${URL_PREFIX}/users/${requestor}/approvals/client/${clientId}/${
            approvalId}/actions/grant`,
        {});
  }

  private readonly flowDescriptors$ =
      this.http
          .get<ApiListClientFlowDescriptorsResult>(
              `${URL_PREFIX}/flows/descriptors`)
          .pipe(
              map(res => res.items ?? []),
              tap(this.showErrors),
              shareReplay(1),  // Cache latest FlowDescriptors.
          );

  listFlowDescriptors(): Observable<ReadonlyArray<ApiFlowDescriptor>> {
    return this.flowDescriptors$;
  }

  listArtifactDescriptors(): Observable<ReadonlyArray<ArtifactDescriptor>> {
    return this.http.get<ApiListArtifactsResult>(`${URL_PREFIX}/artifacts`)
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  private listFlowsForClient(args: ApiListFlowsArgs):
      Observable<ReadonlyArray<ApiFlow>> {
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
    });

    return this.http
        .get<ApiListFlowsResult>(
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
  subscribeToFlowsForClient(args: ApiListFlowsArgs):
      Observable<ReadonlyArray<ApiFlow>> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listFlowsForClient(args)),
            tap(this.showErrors),
        );
  }

  /** Lists all scheduled flows for the given client and user. */
  listScheduledFlows(clientId: string, creator: string):
      Observable<ReadonlyArray<ApiScheduledFlow>> {
    return this.http
        .get<ApiListScheduledFlowsResult>(
            `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${creator}/`)
        .pipe(
            map(res => res.scheduledFlows ?? []),
            tap(this.showErrors),
        );
  }


  /** Lists results of the given flow. */
  listResultsForFlow(params: FlowResultsParams):
      Observable<ReadonlyArray<ApiFlowResult>> {
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
        .get<ApiListFlowResultsResult>(
            `${URL_PREFIX}/clients/${params.clientId}/flows/${
                params.flowId}/results`,
            {params: httpParams})
        .pipe(
            map(res => res.items ?? []),
            tap(this.showErrors),
        );
  }

  // TODO(user): Ideally, HttpApiClient would stop polling when the flow has
  // been completed. This logic is now in the Store.
  /** Continuously lists results for the given flow, e.g. by polling. */
  subscribeToResultsForFlow(params: FlowResultsParams):
      Observable<ReadonlyArray<ApiFlowResult>> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            exhaustMap(() => this.listResultsForFlow(params)),
            tap(this.showErrors),
        );
  }

  /** Starts a Flow on the given Client. */
  startFlow(clientId: string, flowName: string, flowArgs: AnyObject):
      Observable<ApiFlow> {
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
        switchMap((request: ApiCreateFlowArgs) => {
          return this.http
              .post<ApiFlow>(`${URL_PREFIX}/clients/${clientId}/flows`, request)
              .pipe(
                  tap(this.showErrors),
                  catchError(
                      (e: HttpErrorResponse) =>
                          throwError(new Error(e.error.message ?? e.message))),
              );
        }),
    );
  }

  /** Schedules a Flow on the given Client. */
  scheduleFlow(clientId: string, flowName: string, flowArgs: AnyObject):
      Observable<ApiScheduledFlow> {
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
        switchMap((request: ApiCreateFlowArgs) => {
          return this.http
              .post<ApiFlow>(
                  `${URL_PREFIX}/clients/${clientId}/scheduled-flows`, request)
              .pipe(
                  tap(this.showErrors),
                  catchError(
                      (e: HttpErrorResponse) =>
                          throwError(new Error(e.error.message ?? e.message))),
              );
        }),
    );
  }

  /** Cancels the given Flow. */
  cancelFlow(clientId: string, flowId: string): Observable<ApiFlow> {
    const url =
        `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/actions/cancel`;
    return this.http.post<ApiFlow>(url, {}).pipe(
        tap(this.showErrors),
    );
  }

  /** Unschedules a previously scheduled flow. */
  unscheduleFlow(clientId: string, scheduledFlowId: string): Observable<{}> {
    const url =
        `${URL_PREFIX}/clients/${clientId}/scheduled-flows/${scheduledFlowId}`;
    return this.http.delete<{}>(url, {}).pipe(
        tap(this.showErrors),
    );
  }

  /** Fetches the current user. */
  fetchCurrentUser(): Observable<ApiGrrUser> {
    return this.http.get<ApiGrrUser>(`${URL_PREFIX}/users/me`)
        .pipe(
            tap(this.showErrors),
        );
  }

  /** Explains a GlobExpression. */
  explainGlobExpression(
      clientId: string, globExpression: string,
      {exampleCount}: {exampleCount: number}):
      Observable<ReadonlyArray<GlobComponentExplanation>> {
    const url = `${URL_PREFIX}/clients/${clientId}/glob-expressions:explain`;
    const args: ApiExplainGlobExpressionArgs = {globExpression, exampleCount};
    return this.http.post<ApiExplainGlobExpressionResult>(url, args).pipe(
        map(result => result.components ?? []),
        tap(this.showErrors),
    );
  }

  fetchUiConfig(): Observable<ApiUiConfig> {
    return this.http.get<ApiUiConfig>(`${URL_PREFIX}/config/ui`)
        .pipe(
            tap(this.showErrors),
        );
  }


  addClientLabel(clientId: string, label: string): Observable<{}> {
    const url = `${URL_PREFIX}/clients/labels/add`;
    const body:
        ApiAddClientsLabelsArgs = {clientIds: [clientId], labels: [label]};
    return this.http.post<{}>(url, body).pipe(
        tap(this.showErrors),
    );
  }

  removeClientLabel(clientId: string, label: string): Observable<string> {
    const url = `${URL_PREFIX}/clients/labels/remove`;
    const body:
        ApiRemoveClientsLabelsArgs = {clientIds: [clientId], labels: [label]};
    return this.http.post<{}>(url, body).pipe(
        mapTo(label),
        tap(this.showErrors),
        catchError(
            (e: HttpErrorResponse) =>
                throwError(new Error(e.error.message ?? e.message))),
    );
  }

  fetchAllClientsLabels(): Observable<ReadonlyArray<ApiClientLabel>> {
    const url = `${URL_PREFIX}/clients/labels`;
    return this.http.get<ApiListClientsLabelsResult>(url).pipe(
        map(clientsLabels => clientsLabels.items ?? []),
        tap(this.showErrors),
    );
  }

  fetchClientVersions(clientId: string, start?: Date, end?: Date):
      Observable<ReadonlyArray<ApiClient>> {
    const url = `${URL_PREFIX}/clients/${clientId}/versions`;

    const params = new HttpParams({
      fromObject: {
        // If start not set, fetch from beginning of time
        start: ((start?.getTime() ?? 1) * 1000).toString(),
        end: ((end ?? new Date()).getTime() * 1000).toString(),
      }
    });

    return this.http.get<ApiGetClientVersionsResult>(url, {params})
        .pipe(
            map(clientVersions => clientVersions.items ?? []),
            tap(this.showErrors),
        );
  }

  suggestApprovers(usernameQuery: string):
      Observable<ReadonlyArray<ApproverSuggestion>> {
    const params = new HttpParams().set('username_query', usernameQuery);
    return this.http
        .get<ApiListApproverSuggestionsResult>(
            `${URL_PREFIX}/users/approver-suggestions`, {params})
        .pipe(
            map(result => result.suggestions ?? []),
            tap(this.showErrors),
        );
  }

  listRecentClientApprovals(parameters: {count?: number}):
      Observable<ReadonlyArray<ApiClientApproval>> {
    return this.http
        .get<ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client`,
            {params: objectToHttpParams(parameters)})
        .pipe(
            map(result => result.items ?? []),
            tap(this.showErrors),
        );
  }

  getFileDetails(
      clientId: string,
      pathType: PathSpecPathType,
      path: string,
      opts?: {timestamp?: Date},
      ): Observable<ApiFile> {
    const params = objectToHttpParams({timestamp: opts?.timestamp?.getDate()});
    const vfsPath = toVFSPath(pathType, path);
    return this.http
        .get<ApiGetFileDetailsResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-details${vfsPath}`, {params})
        .pipe(
            map(response => response.file ?? {}),
            tap(this.showErrors),
        );
  }

  getFileText(
      clientId: string,
      pathType: PathSpecPathType,
      path: string,
      opts?: GetFileTextOptions,
      ): Observable<ApiGetFileTextResult|null> {
    const queryArgs: ApiGetFileTextArgs = {
      encoding: ApiGetFileTextArgsEncoding.UTF_8,
      offset: 0,
      ...opts,
      timestamp: opts?.timestamp?.getTime(),
    };

    const vfsPath = toVFSPath(pathType, path);
    return this.http
        .get<ApiGetFileTextResult>(
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
      pathType: PathSpecPathType,
      path: string,
      opts?: GetFileBlobOptions,
      ): Observable<bigint|null> {
    const queryArgs: ApiGetFileTextArgs = {
      ...opts,
      timestamp: opts?.timestamp?.getTime(),
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
      pathType: PathSpecPathType,
      path: string,
      opts?: GetFileBlobOptions,
      ): Observable<ArrayBuffer|null> {
    const queryArgs: ApiGetFileTextArgs = {
      encoding: ApiGetFileTextArgsEncoding.UTF_8,
      offset: 0,
      ...opts,
      timestamp: opts?.timestamp?.getTime(),
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

  listFiles(
      clientId: string,
      pathType: PathSpecPathType,
      path: string,
      args?: ApiListFilesArgs,
      ): Observable<ApiListFilesResult> {
    const vfsPath = toVFSPath(pathType, path);

    return this.http
        .get<ApiListFilesResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-index${vfsPath}`, {
              params: objectToHttpParams((args ?? {}) as HttpParamObject),
            })
        .pipe(
            catchError(error404To({})),
            catchError(
                // TODO: ApiListFilesHandler should reply with
                // status 404 when the path is not found.
                (err: HttpErrorResponse) =>
                    (err.status === 500 &&
                     (err.error.message.endsWith('does not exist') ||
                      err.error.message.endsWith('is not a directory'))) ?
                    of({}) :
                    throwError(err)),
            tap(this.showErrors),
        );
  }

  /**
   * Triggers recollection of a file and returns the new ApiFile after
   * the recollection has been finished.
   */
  updateVfsFileContent(
      clientId: string,
      pathType: PathSpecPathType,
      path: string,
      ): Observable<ApiFile> {
    const data:
        ApiUpdateVfsFileContentArgs = {filePath: toVFSPath(pathType, path)};
    return this.http
        .post<ApiUpdateVfsFileContentResult>(
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
      ): Observable<ApiGetVfsFileContentUpdateStateResult> {
    return this.http
        .get<ApiGetVfsFileContentUpdateStateResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-update/${operationId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  private pollVfsFileContentUpdateState(
      clientId: string,
      operationId: string,
      ): Observable<ApiGetVfsFileContentUpdateStateResult> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            switchMap(
                () => this.getVfsFileContentUpdateState(clientId, operationId)),
            takeWhile(
                (response) => response.state ===
                    ApiGetVfsFileContentUpdateStateResultState.RUNNING,
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
      pathType: PathSpecPathType,
      path: string,
      opts?: ApiCreateVfsRefreshOperationArgs,
      ): Observable<ApiListFilesResult> {
    const data: ApiCreateVfsRefreshOperationArgs = {
      filePath: toVFSPath(pathType, path),
      ...opts,
    };
    return this.http
        .post<ApiCreateVfsRefreshOperationResult>(
            `${URL_PREFIX}/clients/${clientId}/vfs-refresh-operations`, data)
        .pipe(
            switchMap(
                response => this.pollVfsRefreshOperationState(
                    clientId, response.operationId!)),
            tap(this.showErrors),
            takeLast(1),
            switchMap(() => this.listFiles(clientId, pathType, path)),
        );
  }

  private getVfsRefreshOperationState(
      clientId: string,
      operationId: string,
      ): Observable<ApiGetVfsRefreshOperationStateResult> {
    return this.http
        .get<ApiGetVfsRefreshOperationStateResult>(`${URL_PREFIX}/clients/${
            clientId}/vfs-refresh-operations/${operationId}`)
        .pipe(
            tap(this.showErrors),
        );
  }

  private pollVfsRefreshOperationState(
      clientId: string,
      operationId: string,
      ): Observable<ApiGetVfsRefreshOperationStateResult> {
    return timer(0, this.POLLING_INTERVAL)
        .pipe(
            switchMap(
                () => this.getVfsRefreshOperationState(clientId, operationId)),
            takeWhile(
                (response) => response.state ===
                    ApiGetVfsRefreshOperationStateResultState.RUNNING,
                true),
            tap(this.showErrors),
        );
  }

  listBinaries() {
    return this.http.get<ApiListGrrBinariesResult>(
        `${URL_PREFIX}/config/binaries`);
  }
}

function toVFSPath(pathType: PathSpecPathType, path: string): string {
  // Encode backslashes, question marks and other characters that break URLs.
  path = path.split('/').map(encodeURIComponent).join('/');
  return '/fs/' + pathType.toLowerCase() + path;
}

interface HttpParamObject {
  [key: string]: string|number|undefined|null;
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
    (fds: ReadonlyArray<ApiFlowDescriptor>) => ApiFlowDescriptor {
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
    clientId: string, pathType: PathSpecPathType, path: string) {
  const vfsPath = toVFSPath(pathType, path);
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
