/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ClientDetailsGlobalStore} from './client_details_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface ClientDetailsGlobalStoreMock extends
    MockStore<ClientDetailsGlobalStore> {}

export function mockClientDetailsGlobalStore() {
  return mockStore(ClientDetailsGlobalStore);
}
