import {
  HttpContextToken,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable, timer} from 'rxjs';
import {exhaustMap, share} from 'rxjs/operators';

/**
 * HttpContextToken for API translation. Polling interval in milliseconds, or 0
 * if polling is not requested.
 */
export const POLLING_INTERVAL = new HttpContextToken(() => 0);

/** Interceptor that translates API responses to the corresponding model types. */
@Injectable()
export class PollingInterceptor implements HttpInterceptor {
  intercept<T>(
    req: HttpRequest<T>,
    handler: HttpHandler,
  ): Observable<HttpEvent<T>> {
    const pollingInterval = req.context.get(POLLING_INTERVAL);
    if (pollingInterval) {
      return timer(0, pollingInterval).pipe(
        exhaustMap(() => handler.handle(req)),
        share(),
      );
    }
    return handler.handle(req);
  }
}
