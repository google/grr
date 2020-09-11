import {Injectable} from '@angular/core';
import {ConfigService} from '@app/components/config/config';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateClient} from '@app/lib/api_translation/client';
import {Client} from '@app/lib/models/client';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, Observable, of, timer} from 'rxjs';
import {filter, map, mergeMap, switchMapTo, tap} from 'rxjs/operators';

interface ClientDetailsState {
  readonly client?: Client;
  readonly clientId?: string;
  readonly clientVersions?: Client[];
}
/**
 * ComponentStore implementation used by the ClientDetailsFacade. Shouldn't be
 * used directly. Declared as an exported global symbol to make dependency
 * injection possible.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientDetailsStore extends ComponentStore<ClientDetailsState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService) {
    super({});
  }

  /** Reducer updating the selected client. */
  private readonly updateSelectedClient =
      this.updater<Client>((state, client) => {
        return {
          ...state,
          client,
        };
      });

  /** Reducer updating the clientId in the store's state. */
  readonly selectClient = this.updater<string>((state, clientId) => {
    return {
      ...state,
      clientId,
    };
  });

  /** An effect fetching a client with a given id and updating the state. */
  private readonly fetchClient = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.select(state => state.clientId)),
          filter((clientId): clientId is string => clientId !== undefined),
          mergeMap(clientId => {
            return this.httpApiService.fetchClient(clientId);
          }),
          map(apiClient => translateClient(apiClient)),
          tap(client => {
            this.updateSelectedClient(client);
          }),
          ));

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> =
      combineLatest(
          timer(0, this.configService.config.selectedClientPollingIntervalMs)
              .pipe(tap(() => this.fetchClient())),
          this.select(state => state.client))
          .pipe(
              map(([i, client]) => client),
              filter((client): client is Client => client !== undefined),
          );

  /** Reducer updating the selected client. */
  private readonly updateSelectedClientVersions =
      this.updater<Client[]>((state, clientVersions) => {
        return {
          ...state,
          clientVersions,
        };
      });

  /** An effect fetching the versions of the selected client */
  private readonly fetchSelectedClientVersions = this.effect<void>(
      obs$ => obs$.pipe(
          switchMapTo(this.select(state => state.clientId)),
          filter((clientId): clientId is string => clientId !== undefined),
          mergeMap(
              clientId => this.httpApiService.fetchClientVersions(clientId)),
          map(apiClientVersions => apiClientVersions.map(translateClient)),
          tap(clientVersions =>
                  this.updateSelectedClientVersions(clientVersions)),
          ));

  /** An observable emitting the client versions of the selected client. */
  readonly selectedClientVersions$: Observable<Client[]> = of(undefined).pipe(
      tap(() => {this.fetchSelectedClientVersions()}),
      switchMapTo(this.select(state => state.clientVersions)),
      filter(
          (clientVersions): clientVersions is Client[] =>
              clientVersions !== undefined),
      // Reverse snapshots to provide reverse chronological order
      map(snapshots => snapshots.slice().reverse()),
  );
}

/** Facade for client details related API calls. */
@Injectable({
  providedIn: 'root',
})
export class ClientDetailsFacade {
  constructor(private readonly store: ClientDetailsStore) {}

  /** An observable emitting the client loaded by `selectClient`. */
  readonly selectedClient$: Observable<Client> = this.store.selectedClient$;

  /** An observable emitting the client versions of the selected client. */
  readonly selectedClientVersions$: Observable<Client[]> =
      this.store.selectedClientVersions$;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.selectClient(clientId);
  }
}
