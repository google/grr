import {NgModule} from '@angular/core';
import {EffectsModule} from '@ngrx/effects';
import {Action, StoreModule, StoreRootModule} from '@ngrx/store';

import {ApiModule} from '../lib/api/module';
import {ClientEffects} from './client/client_effects';
import {clientReducer} from './client/client_reducers';
import {CLIENT_FEATURE} from './client/client_selectors';
import {ClientFacade} from './client_facade';
import {ClientSearchEffects} from './client_search/client_search_effects';
import {clientSearchReducer, ClientSearchState} from './client_search/client_search_reducers';
import {ClientSearchFacade} from './client_search_facade';


/** This is needed only to make AoT compilation happy. */
export function clientSearchReducerWrapper(
    state: ClientSearchState|undefined, action: Action) {
  return clientSearchReducer(state, action);
}

/**
 * Root NgRx store definition.
 */
@NgModule({
  imports: [
    ApiModule,
    StoreModule.forRoot({}, {
      runtimeChecks: {
        // TODO(user): limit to dev mode only.
        strictImmutability: true,
      },
    }),
    StoreModule.forFeature('clientSearch', clientSearchReducerWrapper),
    StoreModule.forFeature(CLIENT_FEATURE, clientReducer),
    EffectsModule.forRoot([ClientSearchEffects, ClientEffects]),
  ],
  providers: [
    ClientSearchFacade,
    ClientFacade,
  ],
  exports: [StoreRootModule]
})
export class GrrStoreModule {
}
