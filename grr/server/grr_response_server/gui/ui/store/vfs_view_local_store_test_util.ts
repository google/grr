/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {MockStore, mockStore} from './store_test_util';
import {VfsViewLocalStore} from './vfs_view_local_store';


export declare interface VfsViewLocalStoreMock extends
    MockStore<VfsViewLocalStore> {}

export function mockVfsViewLocalStore() {
  return mockStore(VfsViewLocalStore);
}
