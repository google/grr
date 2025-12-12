import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';

/** Interceptor that enables the sending of cookies for all HTTP requests. */
@Injectable()
export class WithCredentialsInterceptor implements HttpInterceptor {
  intercept<T>(
    req: HttpRequest<T>,
    next: HttpHandler,
  ): Observable<HttpEvent<T>> {
    return next.handle(
      req.clone({
        withCredentials: true,
        setHeaders: {'X-User-Agent': 'GRR-UI/2.0'},
      }),
    );
  }
}
