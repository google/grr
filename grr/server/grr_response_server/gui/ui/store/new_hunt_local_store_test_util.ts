/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {NewHuntLocalStore} from './new_hunt_local_store';
import {MockStore, mockStore} from './store_test_util';

export interface NewHuntLocalStoreMock extends MockStore<NewHuntLocalStore> {}

export function mockNewHuntLocalStore() {
  return mockStore(NewHuntLocalStore);
}
