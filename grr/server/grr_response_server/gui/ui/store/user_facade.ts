import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {GrrUser} from '@app/lib/models/user';
import {Observable} from 'rxjs';
import {filter} from 'rxjs/operators';

import * as actions from './user/user_actions';
import {UserState} from './user/user_reducers';
import * as selectors from './user/user_selectors';


/** Facade for flow-related API calls. */
@Injectable({
  providedIn: 'root',
})
export class UserFacade {
  constructor(private readonly store: Store<UserState>) {}

  /** An observable emitting the user loaded by fetchCurrentUser. */
  readonly currentUser$: Observable<GrrUser> =
      this.store.select(selectors.currentUser)
          .pipe(
              filter((user): user is GrrUser => user !== undefined),
          );

  fetchCurrentUser() {
    this.store.dispatch(actions.fetchCurrentUser());
  }
}
