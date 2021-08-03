/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols


import {ClientPageGlobalStore} from './client_page_global_store';
import {mockStore, MockStore} from './store_test_util';

export declare interface ClientPageGlobalStoreMock extends
    MockStore<ClientPageGlobalStore> {}

export function mockClientPageGlobalStore() {
  const mock = mockStore(ClientPageGlobalStore);
  mock.mockedObservables.latestApproval$.next(undefined);
  mock.mockedObservables.startFlowState$.next({state: 'request_not_sent'});
  return mock;
}
