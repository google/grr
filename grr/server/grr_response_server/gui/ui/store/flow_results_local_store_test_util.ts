/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {Observable} from 'rxjs';

import {FlowResultsLocalStore} from './flow_results_local_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface FlowResultsLocalStoreMock extends
    MockStore<FlowResultsLocalStore> {}

export function mockFlowResultsLocalStore() {
  const mock = mockStore(FlowResultsLocalStore, {
    query: jasmine.createSpy('query').and.callFake((q) => {
      if (q instanceof Observable) {
        q.subscribe(mock.mockedObservables.query$);
      } else {
        mock.mockedObservables.query$.next(q);
      }
    }),
  });
  return mock;
}
