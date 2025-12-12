import {
  ErrorHandler,
  importProvidersFrom,
  provideZoneChangeDetection,
} from '@angular/core';
import {bootstrapApplication} from '@angular/platform-browser';
import {
  provideRouter,
  withComponentInputBinding,
  withRouterConfig,
} from '@angular/router';

import {App} from './components/app/app';
import {APP_ROUTES} from './components/app/routing';
import {ApiModule} from './lib/api/module';
import {SnackBarErrorHandler} from './lib/error_handler/snackbar_error_handler';

// The "main" for the Angular 2 app. Tells Angular to start doing stuff
// (bootstrap the app).

// Best-effort polyfill for Safari.
window.BigInt = window.BigInt ?? window.Number;

bootstrapApplication(App, {
  providers: [
    importProvidersFrom(ApiModule),
    provideRouter(
      APP_ROUTES,
      withComponentInputBinding(),
      withRouterConfig({
        paramsInheritanceStrategy: 'always',
      }),
    ),
    provideZoneChangeDetection(),
    {provide: ErrorHandler, useClass: SnackBarErrorHandler},
  ],
});
