import {CommonModule} from '@angular/common';
import {ErrorHandler, NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule, MatIconRegistry} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatTabsModule} from '@angular/material/tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouteReuseStrategy} from '@angular/router';

import {ClientPageModule} from '../../components/client_page/client_page_module';
import {ClientSearchModule} from '../../components/client_search/module';
import {HomeModule} from '../../components/home/module';
import {HuntApprovalPageModule} from '../../components/hunt/hunt_approval_page/hunt_approval_page_module';
import {HuntPageModule} from '../../components/hunt/hunt_page/module';
import {NewHuntModule} from '../../components/hunt/new_hunt/module';
import {UserMenuModule} from '../../components/user_menu/module';
import {ApiModule} from '../../lib/api/module';
import {SameComponentRouteReuseStrategy} from '../../lib/routing';
import {ApprovalPageModule} from '../approval_page/approval_page_module';
import {FileDetailsModule} from '../file_details/file_details_module';
import {SnackBarErrorHandler} from '../helpers/error_snackbar/error_handler';
import {ErrorSnackBarModule} from '../helpers/error_snackbar/error_snackbar_module';
import {HuntOverviewPage} from '../hunt/hunt_overview_page/hunt_overview_page';
// import {HuntProgress} from '../hunt/hunt_progress/hunt_progress';

import {App} from './app';
import {NotFoundPage} from './not_found_page';
import {AppRoutingModule} from './routing';


const ANGULAR_MATERIAL_MODULES = [
  MatButtonModule,
  MatIconModule,
  MatSidenavModule,
  MatSnackBarModule,
  MatTabsModule,
  MatToolbarModule,
  MatTooltipModule,
];

const GRR_MODULES = [
  ApiModule,
  ApprovalPageModule,
  ClientSearchModule,
  ClientPageModule,
  ErrorSnackBarModule,
  FileDetailsModule,
  HomeModule,
  NewHuntModule,
  UserMenuModule,
  HuntOverviewPage,
  HuntPageModule,
  // HuntProgress,
  HuntApprovalPageModule,
];

/**
 * The main application module.
 */
@NgModule({
  declarations: [
    App,
    NotFoundPage,
  ],
  imports: [
    CommonModule,
    BrowserAnimationsModule,
    ...ANGULAR_MATERIAL_MODULES,
    ...GRR_MODULES,
    // Should be the last to make sure all module-specific routes are
    // already registered by the time it's imported.
    AppRoutingModule,
  ],
  providers: [
    {provide: RouteReuseStrategy, useClass: SameComponentRouteReuseStrategy},
    // Register SnackBarErrorHandler as default error handler for whole app.
    {provide: ErrorHandler, useClass: SnackBarErrorHandler},
  ],
  bootstrap: [App],
  exports: [NotFoundPage]
})
export class AppModule {
  constructor(iconRegistry: MatIconRegistry) {
    iconRegistry.setDefaultFontSetClass('material-icons-outlined');
  }
}

/**
 * The main application module with dev tools support. It enables integration
 * with Chrome's Redux Devltools extension.
 */
@NgModule({
  imports: [
    AppModule,
  ],
  providers: [],
  bootstrap: [App]
})
export class DevAppModule {
}
