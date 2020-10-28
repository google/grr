/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {Client} from '../lib/models/client';

import {ClientVersion} from './client_details_diff';
import {ClientDetailsFacade} from './client_details_facade';

export declare interface ClientDetailsFacadeMock extends
    Partial<ClientDetailsFacade> {
  readonly selectedClientVersionsSubject: Subject<ReadonlyArray<ClientVersion>>;
  readonly selectedClientEntriesChangedSubject:
      Subject<Map<string, ReadonlyArray<Client>>>;
}

export function mockClientDetailsFacade(): ClientDetailsFacadeMock {
  const selectedClientVersionsSubject =
      new ReplaySubject<ReadonlyArray<ClientVersion>>(1);
  const selectedClientEntriesChangedSubject =
      new ReplaySubject<Map<string, ReadonlyArray<Client>>>(1);

  return {
    selectClient: jasmine.createSpy('selectClient'),
    selectedClientVersionsSubject,
    selectedClientVersions$: selectedClientVersionsSubject.asObservable(),
    selectedClientEntriesChangedSubject,
    selectedClientEntriesChanged$:
        selectedClientEntriesChangedSubject.asObservable(),
  };
}
