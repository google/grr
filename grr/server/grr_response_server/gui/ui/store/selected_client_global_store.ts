import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable} from 'rxjs';


interface State {
  clientId: string|null;
}

class SelectedClientStore extends ComponentStore<State> {
  constructor() {
    super({clientId: null});
  }

  readonly selectClientId = this.updater<string|null>((state, clientId) => {
    return {...state, clientId};
  });

  readonly clientId$ = this.select(state => state.clientId);
}


/** Store to globally mark a client ID as selected. */
@Injectable({providedIn: 'root'})
export class SelectedClientGlobalStore {
  private readonly store = new SelectedClientStore();

  /** The currently selected client, or null if no client is selected. */
  readonly clientId$: Observable<string|null> = this.store.clientId$;

  /** Selects a client ID, or null to indicate no current client. */
  selectClientId(clientId: string|null|Observable<string|null>) {
    this.store.selectClientId(clientId);
  }
}
