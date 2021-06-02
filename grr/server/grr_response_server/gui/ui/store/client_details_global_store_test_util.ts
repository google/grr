/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {Client} from '../lib/models/client';

import {ClientVersion} from './client_details_diff';
import {ClientDetailsGlobalStore} from './client_details_global_store';

export declare interface ClientDetailsGlobalStoreMock extends
    Partial<ClientDetailsGlobalStore> {
  readonly selectedClientVersionsSubject: Subject<ReadonlyArray<ClientVersion>>;
  readonly selectedClientEntriesChangedSubject:
      Subject<Map<string, ReadonlyArray<Client>>>;
}

export function mockClientDetailsGlobalStore(): ClientDetailsGlobalStoreMock {
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
