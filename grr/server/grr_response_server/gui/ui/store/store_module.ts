import {NgModule} from '@angular/core';
import {EffectsModule} from '@ngrx/effects';
import {StoreModule, StoreRootModule} from '@ngrx/store';
import {UserEffects} from '@app/store/user/user_effects';
import {ApiModule} from '../lib/api/module';
import {ClientPageEffects} from './client_page/client_page_effects';
import {clientPageReducer} from './client_page/client_page_reducers';
import {CLIENT_PAGE_FEATURE} from './client_page/client_page_selectors';
import {ClientSearchEffects} from './client_search/client_search_effects';
import {clientSearchReducer} from './client_search/client_search_reducers';
import {CLIENT_SEARCH_FEATURE} from './client_search/client_search_selectors';
import {ConfigEffects} from './config/config_effects';
import {configReducer} from './config/config_reducers';
import {CONFIG_FEATURE} from './config/config_selectors';
import {userReducer} from './user/user_reducers';
import {USER_FEATURE} from './user/user_selectors';



declare global {
  interface Window {
    // These are references to external window definitions.
    // tslint:disable-next-line:enforce-name-casing
    __IS_GRR_TEST?: boolean;
    // tslint:disable-next-line:enforce-name-casing
    __IS_GRR_DEVELOPMENT?: boolean;
  }
}

const enableRuntimeChecks = window.__IS_GRR_TEST || window.__IS_GRR_DEVELOPMENT;

/**
 * Root NgRx store definition.
 */
@NgModule({
  imports: [
    ApiModule,
    StoreModule.forRoot({}, {
      runtimeChecks: {
        strictStateImmutability: enableRuntimeChecks,
        strictActionImmutability: enableRuntimeChecks,
      },
    }),
    StoreModule.forFeature(CONFIG_FEATURE, configReducer),
    StoreModule.forFeature(CLIENT_SEARCH_FEATURE, clientSearchReducer),
    StoreModule.forFeature(CLIENT_PAGE_FEATURE, clientPageReducer),
    StoreModule.forFeature(USER_FEATURE, userReducer),
    EffectsModule.forRoot([
      ConfigEffects,
      ClientSearchEffects,
      ClientPageEffects,
      UserEffects,
    ]),
  ],
  providers: [],
  exports: [StoreRootModule]
})
export class GrrStoreModule {
}
