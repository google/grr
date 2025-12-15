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
export const SHOW_ERROR_BAR = new HttpContextToken(() => false);
/**
 * HttpContextToken for enabling the error bar for 403 errors.
 */
export const SHOW_ERROR_BAR_FOR_403 = new HttpContextToken(() => true);
/**
 * HttpContextToken for enabling the error bar for 404 errors.
 */
export const SHOW_ERROR_BAR_FOR_404 = new HttpContextToken(() => true);

/** Interceptor that translates API responses to the corresponding model types. */
@Injectable()
export class ShowErrorBarInterceptor implements HttpInterceptor {
  private readonly errorHandler = inject(SnackBarErrorHandler);

  private readonly showError = (response: HttpErrorResponse) => {
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
      message = `Received status ${response.status} ${response.statusText} from ${address}`;
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
          return EMPTY;
        }
        if (response.status === 404 && !showErrorBarFor404) {
          return EMPTY;
        }
        this.showError(response);
        return EMPTY;
      }),
    );
  }
}
