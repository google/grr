import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable} from 'rxjs';
import {filter, map, mergeMap, switchMapTo, tap} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {translateClient} from '../lib/api_translation/client';
import {Client} from '../lib/models/client';
import {isNonNull} from '../lib/preconditions';

import {ClientVersion, getClientEntriesChanged, getClientVersions} from './client_details_diff';

interface ClientDetailsState {
  readonly client?: Client;
  readonly clientId?: string;
  readonly clientSnapshots?: ReadonlyArray<Client>;
  readonly clientVersions?: ReadonlyArray<ClientVersion>;
  readonly clientEntriesChanged?: Map<string, ReadonlyArray<Client>>;
}
/** ComponentStore implementation used by the ClientDetailsGlobalStore. */
class ClientDetailsComponentStore extends ComponentStore<ClientDetailsState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});

    this.clientId$.subscribe(clientId => {
      this.fetchSelectedClientSnapshots();
    });
  }

  /** Reducer updating the clientId in the store's state. */
  readonly updateClientId = this.updater<string>((state, clientId) => {
    return {
      ...state,
      clientId,
    };
  });

  /** Reducer updating the selected client snapshots. */
  private readonly updateClientSnapshots =
      this.updater<Client[]>((state, clientSnapshots) => {
        return {
          ...state,
          clientSnapshots,
        };
      });

  /** Reducer updating the selected client versions. */
  private readonly updateClientVersions =
      this.updater<ClientVersion[]>((state, clientVersions) => {
        return {
          ...state,
          clientVersions,
        };
      });

  /** Reducer updating the selected client versions. */
  private readonly updateClientEntriesChanged =
      this.updater<Map<string, ReadonlyArray<Client>>>(
          (state, clientEntriesChanged) => {
            return {
              ...state,
              clientEntriesChanged,
            };
          });

  private readonly clientId$ = this.select(store => store.clientId);

  /** An effect fetching the versions of the selected client */
  private readonly fetchSelectedClientSnapshots = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.select(state => state.clientId)),
          filter((clientId): clientId is string => clientId !== undefined),
          mergeMap(
              clientId => this.httpApiService.fetchClientVersions(clientId)),
          map(apiClientVersions => apiClientVersions.map(translateClient)),
          // Reverse snapshots to provide reverse chronological order
          map(snapshots => snapshots.slice().reverse()),
          tap(clientSnapshots => {
            this.updateClientSnapshots(clientSnapshots);
            this.updateClientVersions(getClientVersions(clientSnapshots));
            this.updateClientEntriesChanged(
                getClientEntriesChanged(clientSnapshots));
          }),
          ));

  /** An observable emitting the client versions of the selected client */
  readonly selectedClientVersions$ =
      this.select(store => store.clientVersions).pipe(filter(isNonNull));

  /**
   * An observable emitting the client changed entries of the selected client
   */
  readonly selectedClientEntriesChanged$ =
      this.select(store => store.clientEntriesChanged)
          .pipe(filter(
              (clientEntriesChanged):
                  clientEntriesChanged is Map<string, ReadonlyArray<Client>> =>
                      clientEntriesChanged !== undefined));
}

/** GlobalStore for client details related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientDetailsGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ClientDetailsComponentStore(this.httpApiService);

  /** An observable emitting the client versions of the selected client. */
  readonly selectedClientVersions$: Observable<ReadonlyArray<ClientVersion>> =
      this.store.selectedClientVersions$;

  /**
   * An observable emitting the client changed entries of the selected client
   */
  readonly selectedClientEntriesChanged$:
      Observable<Map<string, ReadonlyArray<Client>>> =
          this.store.selectedClientEntriesChanged$;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.updateClientId(clientId);
  }
}
