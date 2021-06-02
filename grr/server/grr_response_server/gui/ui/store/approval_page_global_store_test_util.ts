/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ClientApproval} from '../lib/models/client';

import {ApprovalPageGlobalStore} from './approval_page_global_store';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface ApprovalPageGlobalStoreMock extends
    I<ApprovalPageGlobalStore> {
  approvalSubject: Subject<ClientApproval>;
}

export function mockApprovalPageGlobalStore(): ApprovalPageGlobalStoreMock {
  const approvalSubject = new ReplaySubject<ClientApproval>(1);

  return {
    approvalSubject,
    approval$: approvalSubject.asObservable(),
    selectApproval: jasmine.createSpy('selectApproval'),
    grantApproval: jasmine.createSpy('grantApproval'),
  };
}
