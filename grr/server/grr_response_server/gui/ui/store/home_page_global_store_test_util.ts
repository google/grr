/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ClientApproval} from '../lib/models/client';

import {HomePageGlobalStore} from './home_page_global_store';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface HomePageGlobalStoreMock extends
    I<HomePageGlobalStore> {
  recentClientApprovalsSubject: Subject<ReadonlyArray<ClientApproval>>;
}

export function mockHomePageGlobalStore(): HomePageGlobalStoreMock {
  const recentClientApprovalsSubject =
      new ReplaySubject<ReadonlyArray<ClientApproval>>(1);

  return {
    recentClientApprovals$: recentClientApprovalsSubject.asObservable(),
    recentClientApprovalsSubject,
  };
}
