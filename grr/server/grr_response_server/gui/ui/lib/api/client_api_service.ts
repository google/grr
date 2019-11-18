import {HttpClient, HttpParams} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {ApiClient, ApiSearchClientArgs, ApiSearchClientResult} from './client_api';


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
}
