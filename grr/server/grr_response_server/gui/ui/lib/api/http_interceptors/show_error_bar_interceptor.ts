import {
  HttpContextToken,
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import {Injectable, inject} from '@angular/core';
import {EMPTY, Observable} from 'rxjs';
import {catchError} from 'rxjs/operators';

import {SnackBarErrorHandler} from '../../../lib/error_handler/snackbar_error_handler';

/**
 * HttpContextToken for enabling the error bar.
 */
export const SHOW_ERROR_BAR = new HttpContextToken(() => true);
/**
 * HttpContextToken for enabling the error bar for 403 errors, if the error bar
 * is disablied a MissingApprovalError will be thrown instead.
 */
export const SHOW_ERROR_BAR_FOR_403 = new HttpContextToken(() => true);

/** Access denied because the requestor is missing a valid approval. */
export class MissingApprovalError extends Error {
  constructor(response: HttpErrorResponse) {
    super(response.error?.message ?? response.message);
  }
}

/**
 * HttpContextToken for enabling the error bar for 404 errors, if the error bar
 * is disablied a MissingFileError will be thrown instead.
 */
export const SHOW_ERROR_BAR_FOR_404 = new HttpContextToken(() => true);

/** Access denied because the requested file is missing. */
export class MissingFileError extends Error {
  constructor(response: HttpErrorResponse) {
    super(response.error?.message ?? response.message);
  }
}

/** Interceptor that translates API responses to the corresponding model types. */
@Injectable()
export class ShowErrorBarInterceptor implements HttpInterceptor {
  private readonly errorHandler = inject(SnackBarErrorHandler);

  private readonly showErrorBar = (response: HttpErrorResponse) => {
    const error = response.error;
    const address = response.url ?? 'unknown';
    let message = '';

    if (error instanceof ProgressEvent) {
      message = `Cannot reach ${address}`;
    } else if (response.headers.get('content-type')?.startsWith('text/html')) {
      // During auth problems, proxies might render fully-fledged HTML pages,
      // ignoring the fact that our request accepts JSON only. Showing the raw
      // HTML document provides no value to the user, thus we only show the
      // HTTP status code.
      message = `Received status ${response.status} ${response.message} from ${address}`;
    } else {
      message = `${error['message'] ?? error} (from ${address})`;
    }

    this.errorHandler.handleError(message);
  };

  intercept<T>(
    req: HttpRequest<T>,
    handler: HttpHandler,
  ): Observable<HttpEvent<T>> {
    const showErrorBar = req.context.get(SHOW_ERROR_BAR);
    const showErrorBarFor403 = req.context.get(SHOW_ERROR_BAR_FOR_403);
    const showErrorBarFor404 = req.context.get(SHOW_ERROR_BAR_FOR_404);
    if (!showErrorBar) {
      return handler.handle(req);
    }
    return handler.handle(req).pipe(
      catchError((response: HttpErrorResponse) => {
        if (response.status === 403 && !showErrorBarFor403) {
          throw new MissingApprovalError(response);
        }
        if (response.status === 404 && !showErrorBarFor404) {
          throw new MissingFileError(response);
        }
        this.showErrorBar(response);
        return EMPTY;
      }),
    );
  }
}
