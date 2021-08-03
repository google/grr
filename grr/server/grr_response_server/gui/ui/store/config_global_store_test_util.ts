/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ConfigGlobalStore} from './config_global_store';
import {mockStore, MockStore} from './store_test_util';

export type ConfigGlobalStoreMock = MockStore<ConfigGlobalStore>;
export const mockConfigGlobalStore = () => mockStore(ConfigGlobalStore);
