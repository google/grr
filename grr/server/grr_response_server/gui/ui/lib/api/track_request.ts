
import {HttpErrorResponse} from '@angular/common/http';
import {merge, Observable, of, throwError} from 'rxjs';
import {catchError, map} from 'rxjs/operators';


/** Enum describing the state of a {@link RequestStatus}. */
export enum RequestStatusType {
  SENT,
  SUCCESS,
  ERROR,
}

interface SentRequestStatus {
  readonly status: RequestStatusType.SENT;
}

interface ErrorRequestStatus<Error = HttpErrorResponse> {
  readonly status: RequestStatusType.ERROR;
  readonly error: Error;
}

interface SuccessRequestStatus<Success> {
  readonly status: RequestStatusType.SUCCESS;
  readonly data: Success;
}

/** Status (sent, error, success) of network requests. */
export type RequestStatus<Success = undefined, Error = HttpErrorResponse> =
    SentRequestStatus|SuccessRequestStatus<Success>|ErrorRequestStatus<Error>;

/**
 * Tracks a HTTP request, first emitting SENT, then SUCCESS or ERROR.
 *
 * If the resulting HTTP response is unsuccessful (4XX, 5XX code), the returned
 * Observable will NOT error, instead trackRequest will emit an ERROR value.
 */
export function trackRequest<S>(request: Observable<S>):
    Observable<RequestStatus<S>> {
  return merge(
             of<SentRequestStatus>({status: RequestStatusType.SENT}),
             request.pipe(map<S, SuccessRequestStatus<S>>(
                 data => ({status: RequestStatusType.SUCCESS, data}))),
             )
      .pipe(
          catchError((error) => {
            if (error instanceof HttpErrorResponse) {
              return of<ErrorRequestStatus>(
                  {status: RequestStatusType.ERROR, error});
            } else {
              return throwError(error);
            }
          }),
      );
}

/**
 * Passes through the RequestStatus, but extracts the string error message out
 * of a possible HttpErrorResponse.
 */
export function extractErrorMessage<S>(
    requestStatus: RequestStatus<S, HttpErrorResponse>):
    RequestStatus<S, string> {
  if (requestStatus.status === RequestStatusType.ERROR) {
    return {
      status: RequestStatusType.ERROR,
      error: (requestStatus.error.error?.message ?? requestStatus.error.message)
                 .toString(),
    };
  } else {
    return requestStatus;
  }
}
