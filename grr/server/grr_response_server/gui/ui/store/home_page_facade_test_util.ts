/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ClientApproval} from '../lib/models/client';

import {HomePageFacade} from './home_page_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface HomePageFacadeMock extends I<HomePageFacade> {
  recentClientApprovalsSubject: Subject<ReadonlyArray<ClientApproval>>;
}

export function mockHomePageFacade(): HomePageFacadeMock {
  const recentClientApprovalsSubject =
      new ReplaySubject<ReadonlyArray<ClientApproval>>(1);

  return {
    recentClientApprovals$: recentClientApprovalsSubject.asObservable(),
    recentClientApprovalsSubject,
  };
}
