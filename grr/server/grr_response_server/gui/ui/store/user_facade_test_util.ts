/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';
import {GrrUser} from '../lib/models/user';
import {UserFacade} from './user_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface UserFacadeMock extends I<UserFacade> {
  currentUserSubject: Subject<GrrUser>;
}

export function mockUserFacade(): UserFacadeMock {
  const currentUserSubject = new ReplaySubject<GrrUser>(1);

  return {
    currentUserSubject,
    currentUser$: currentUserSubject.asObservable(),
  };
}
