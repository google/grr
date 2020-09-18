/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ClientApproval} from '../lib/models/client';

import {ApprovalPageFacade} from './approval_page_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface ApprovalPageFacadeMock extends I<ApprovalPageFacade> {
  approvalSubject: Subject<ClientApproval>;
}

export function mockApprovalPageFacade(): ApprovalPageFacadeMock {
  const approvalSubject = new ReplaySubject<ClientApproval>(1);

  return {
    approvalSubject,
    approval$: approvalSubject.asObservable(),
    selectApproval: jasmine.createSpy('selectApproval'),
    grantApproval: jasmine.createSpy('grantApproval'),
  };
}
