import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {Observable} from 'rxjs';
import {filter} from 'rxjs/operators';

import {Client} from '../lib/models/client';
import * as actions from './client/client_actions';
import {ClientState} from './client/client_reducers';
import * as selectors from './client/client_selectors';

function notUndefined(client?: Client): client is Client {
  return client !== undefined;
}

/** Facade for client-related API calls. */
@Injectable()
export class ClientFacade {
  constructor(private readonly store: Store<ClientState>) {}

  /** An observable emitting the client loaded by `fetchClient`. */
  readonly client$: Observable<Client> =
      this.store.select(selectors.client).pipe(filter(notUndefined));

  /** Loads a client by its ID, to be emitted in `client$`. */
  fetchClient(id: string): void {
    this.store.dispatch(actions.fetch({id}));
  }
}
