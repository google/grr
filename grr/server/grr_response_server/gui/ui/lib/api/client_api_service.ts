import {HttpClient, HttpParams} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {ApprovalConfig, ApprovalRequest} from '@app/lib/models/client';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {ApiApprovalOptionalCcAddressResult, ApiClient, ApiClientApproval, ApiListClientApprovalsResult, ApiSearchClientArgs, ApiSearchClientResult} from './client_api';


/**
 * Common prefix for all API calls.
 */
const URL_PREFIX = '/api/v2';

/**
 * Service to make client-related HTTP requests to GRR API endpoint.
 */
@Injectable()
export class ClientApiService {
  constructor(private readonly http: HttpClient) {}

  /**
   * Searches for clients using given API arguments.
   */
  searchClients(args: ApiSearchClientArgs): Observable<ApiSearchClientResult> {
    const url = URL_PREFIX + '/clients';

    const params = new HttpParams().set('query', args.query || '');
    if (args.offset) {
      params.set('offset', args.offset.toString());
    }
    if (args.count) {
      params.set('count', args.count.toString());
    }

    return this.http.get<ApiSearchClientResult>(
        url, {params, withCredentials: true});
  }

  /** Fetches a client by its ID. */
  fetchClient(id: string): Observable<ApiClient> {
    return this.http.get<ApiClient>(
        `${URL_PREFIX}/clients/${id}`, {withCredentials: true});
  }

  /** Requests approval to give the current user access to a client. */
  requestApproval(args: ApprovalRequest): Observable<void> {
    const request = {
      approval: {
        reason: args.reason,
        notified_users: args.approvers,
        email_cc_addresses: args.cc,
      },
    };

    return this.http
        .post<void>(
            `${URL_PREFIX}/users/me/approvals/client/${args.clientId}`, request,
            {withCredentials: true})
        .pipe(
            map(() => undefined),  // The returned Client Approval is unused.
        );
  }

  fetchApprovalConfig(): Observable<ApprovalConfig> {
    return this.http
        .get<ApiApprovalOptionalCcAddressResult>(
            `${URL_PREFIX}/config/Email.approval_optional_cc_address`,
            {withCredentials: true})
        .pipe(
            // Replace empty string (protobuf default) with undefined.
            map(res => (res.value || {}).value || undefined),
            map(optionalCcEmail => ({optionalCcEmail})),
        );
  }

  /** Lists ClientApprovals in reversed chronological order. */
  listApprovals(clientId: string): Observable<ApiClientApproval[]> {
    return this.http
        .get<ApiListClientApprovalsResult>(
            `${URL_PREFIX}/users/me/approvals/client/${clientId}`,
            {withCredentials: true})
        .pipe(
            map(res => res.items),
        );
  }
}
