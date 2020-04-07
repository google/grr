import {HttpClient, HttpEvent, HttpHandler, HttpInterceptor, HttpParams, HttpRequest} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {ApprovalConfig, ApprovalRequest} from '@app/lib/models/client';
import {Observable} from 'rxjs';
import {map, shareReplay, switchMap, take} from 'rxjs/operators';

import {AnyObject, ApiApprovalOptionalCcAddressResult, ApiClient, ApiClientApproval, ApiCreateClientApprovalArgs, ApiCreateFlowArgs, ApiFlow, ApiFlowDescriptor, ApiGrrUser, ApiListClientApprovalsResult, ApiListClientFlowDescriptorsResult, ApiListFlowsResult, ApiSearchClientArgs, ApiSearchClientResult} from './api_interfaces';


/**
 * Common prefix for all API calls.
 */
const URL_PREFIX = '/api/v2';

/** Interceptor that enables the sending of cookies for all HTTP requests. */
@Injectable()
export class WithCredentialsInterceptor implements HttpInterceptor {
  intercept<T>(req: HttpRequest<T>, next: HttpHandler):
      Observable<HttpEvent<T>> {
    return next.handle(req.clone({withCredentials: true}));
  }
}

/**
 * Service to make HTTP requests to GRR API endpoint.
 */
@Injectable()
export class HttpApiService {
  constructor(private readonly http: HttpClient) {}

  /**
   * Searches for clients using given API arguments.
   */
  searchClients(args: ApiSearchClientArgs): Observable<ApiSearchClientResult> {
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

  /** Fetches a client by its ID. */
  fetchClient(id: string): Observable<ApiClient> {
    return this.http.get<ApiClient>(`${URL_PREFIX}/clients/${id}`);
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
        );
  }

  /** Lists ClientApprovals in reversed chronological order. */
  listApprovals(clientId: string):
      Observable<ReadonlyArray<ApiClientApproval>> {
    return this.http
        .get<ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client/${clientId}`)
        .pipe(
            map(res => res.items),
        );
  }

  private readonly flowDescriptors$ =
      this.http
          .get<ApiListClientFlowDescriptorsResult>(
              `${URL_PREFIX}/flows/descriptors`)
          .pipe(
              map(res => res.items),
              shareReplay(1),  // Cache latest FlowDescriptors.
          );

  listFlowDescriptors(): Observable<ReadonlyArray<ApiFlowDescriptor>> {
    return this.flowDescriptors$;
  }

  /** Lists the latest Flows for the given Client. */
  listFlowsForClient(clientId: string): Observable<ReadonlyArray<ApiFlow>> {
    // TODO(user): make the minStartedAt configurable, take it from the
    // NgRx store.
    // Set minStartedAt to 3 months in the past from now.
    const minStartedAt = (Date.now() - 1000 * 60 * 60 * 24 * 180) * 1000;
    const params = new HttpParams({
      fromObject: {
        count: '100',
        offset: '0',
        min_started_at: minStartedAt.toString(),
        top_flows_only: '1',
      }
    });
    return this.http
        .get<ApiListFlowsResult>(
            `${URL_PREFIX}/clients/${clientId}/flows`, {params})
        .pipe(map(res => res.items));
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
          return this.http.post<ApiFlow>(
              `${URL_PREFIX}/clients/${clientId}/flows`, request);
        }),
    );
  }

  /** Cancels the given Flow. */
  cancelFlow(clientId: string, flowId: string): Observable<ApiFlow> {
    const url =
        `${URL_PREFIX}/clients/${clientId}/flows/${flowId}/actions/cancel`;
    return this.http.post<ApiFlow>(url, {});
  }

  /** Fetches the current user. */
  fetchCurrentUser(): Observable<ApiGrrUser> {
    return this.http.get<ApiGrrUser>(`${URL_PREFIX}/users/me`);
  }
}

function findFlowDescriptor(flowName: string):
    (fds: ReadonlyArray<ApiFlowDescriptor>) => ApiFlowDescriptor {
  return fds => {
    const fd = fds.find(fd => fd.name === flowName);
    if (!fd) throw new Error(`FlowDescriptors do not contain ${flowName}.`);
    return fd;
  };
}
