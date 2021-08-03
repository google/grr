/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {FileDetailsLocalStore} from './file_details_local_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface FileDetailsLocalStoreMock extends
    MockStore<FileDetailsLocalStore> {}

export function mockFileDetailsLocalStore() {
  return mockStore(FileDetailsLocalStore);
}
