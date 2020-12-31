import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {ClientPageModule} from '@app/components/client_page/module';
import {ClientSearchModule} from '@app/components/client_search/module';
import {HomeModule} from '@app/components/home/module';
import {UserMenuModule} from '@app/components/user_menu/module';
import {ApiModule} from '@app/lib/api/module';

import {ApprovalPageModule} from '../approval_page/approval_page_module';

import {App} from './app';
import {AppRoutingModule} from './routing';


const ANGULAR_MATERIAL_MODULES = [
  MatButtonModule,
  MatIconModule,
  MatToolbarModule,
  MatTooltipModule,
];

const GRR_MODULES = [
  ApiModule,
  ClientSearchModule,
  ClientPageModule,
  HomeModule,
  UserMenuModule,
  ApprovalPageModule,
];

/**
 * The main application module.
 */
@NgModule({
  declarations: [
    App,
  ],
  imports: [
    BrowserAnimationsModule,
    ...ANGULAR_MATERIAL_MODULES,
    ...GRR_MODULES,
    // Should be the last to make sure all module-specific routes are
    // already registered by the time it's imported.
    AppRoutingModule,
  ],
  providers: [],
  bootstrap: [App]
})
export class AppModule {
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
