import {
  HttpContextToken,
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpResponse,
} from '@angular/common/http';
import {Injectable, inject} from '@angular/core';
import {Observable} from 'rxjs';
import {tap} from 'rxjs/operators';
import {LoadingService} from '../../service/loading_service/loading_service';

/**
 * HttpContextToken to track the loading state of API requests.
 */
export const TRACK_LOADING_STATE = new HttpContextToken(() => false);

/**
 * Interceptor that tracks the loading state of API requests.
 */
@Injectable()
export class LoadingInterceptor implements HttpInterceptor {
  loadingService = inject(LoadingService);

  intercept<T>(
    req: HttpRequest<T>,
    handler: HttpHandler,
  ): Observable<HttpEvent<T>> {
    if (!req.context.get(TRACK_LOADING_STATE)) {
      return handler.handle(req);
    }

    this.loadingService.updateLoadingUrls(req.url, true);
    return handler.handle(req).pipe(
      tap({
        error: (response: HttpErrorResponse) => {
          this.loadingService.updateLoadingUrls(req.url, false);
          return response;
        },
        next: (response: HttpEvent<T>) => {
          if (response instanceof HttpResponse) {
            this.loadingService.updateLoadingUrls(req.url, false);
          }
          return response;
        },
      }),
    );
  }
}
