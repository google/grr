/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {GrrUser} from '../lib/models/user';

import {UserGlobalStore} from './user_global_store';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface UserGlobalStoreMock extends I<UserGlobalStore> {
  currentUserSubject: Subject<GrrUser>;
}

export function mockUserGlobalStore(): UserGlobalStoreMock {
  const currentUserSubject = new ReplaySubject<GrrUser>(1);

  return {
    currentUserSubject,
    currentUser$: currentUserSubject.asObservable(),
  };
}
