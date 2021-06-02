/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {Observable, ReplaySubject, Subject} from 'rxjs';

import {FlowResult, FlowResultsQuery} from '../lib/models/flow';

import {FlowResultsLocalStore} from './flow_results_local_store';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface FlowResultsLocalStoreMock extends
    I<FlowResultsLocalStore> {
  resultsSubject: Subject<ReadonlyArray<FlowResult>>;
}

export function mockFlowResultsLocalStore(): FlowResultsLocalStoreMock {
  const resultsSubject = new ReplaySubject<ReadonlyArray<FlowResult>>();
  const querySubject = new ReplaySubject<FlowResultsQuery>();

  return {
    resultsSubject,
    results$: resultsSubject.asObservable(),
    query$: querySubject.asObservable(),
    query: jasmine.createSpy('query').and.callFake((q) => {
      if (q instanceof Observable) {
        q.subscribe(querySubject);
      } else {
        querySubject.next(q);
      }
    }),
    queryMore: jasmine.createSpy('queryMore'),
  };
}
