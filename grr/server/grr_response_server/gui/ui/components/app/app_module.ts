import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatTabsModule} from '@angular/material/tabs';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {ClientPageModule} from '../../components/client_page/client_page_module';
import {ClientSearchModule} from '../../components/client_search/module';
import {HomeModule} from '../../components/home/module';
import {HuntPageModule} from '../../components/hunt/hunt_page/module';
import {NewHuntModule} from '../../components/hunt/new_hunt/module';
import {UserMenuModule} from '../../components/user_menu/module';
import {ApiModule} from '../../lib/api/module';
import {ApprovalPageModule} from '../approval_page/approval_page_module';
import {FileDetailsModule} from '../file_details/file_details_module';

import {App} from './app';
import {NotFoundPage} from './not_found_page';
import {AppRoutingModule} from './routing';


const ANGULAR_MATERIAL_MODULES = [
  MatButtonModule,
  MatIconModule,
  MatSidenavModule,
  MatTabsModule,
  MatToolbarModule,
  MatTooltipModule,
];

const GRR_MODULES = [
  ApiModule,
  ApprovalPageModule,
  ClientSearchModule,
  ClientPageModule,
  FileDetailsModule,
  HomeModule,
  NewHuntModule,
  UserMenuModule,
  HuntPageModule,
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
    BrowserAnimationsModule,
    ...ANGULAR_MATERIAL_MODULES,
    ...GRR_MODULES,
    // Should be the last to make sure all module-specific routes are
    // already registered by the time it's imported.
    AppRoutingModule,
  ],
  providers: [],
  bootstrap: [App],
  exports: [NotFoundPage]
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
