/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {SelectedClientGlobalStore} from './selected_client_global_store';
import {MockStore, mockStore} from './store_test_util';

export interface SelectedClientGlobalStoreMock extends
    MockStore<SelectedClientGlobalStore> {}

export function mockSelectedClientGlobalStore() {
  return mockStore(SelectedClientGlobalStore);
}
