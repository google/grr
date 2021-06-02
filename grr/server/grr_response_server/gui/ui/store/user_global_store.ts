import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateGrrUser} from '@app/lib/api_translation/user';
import {GrrUser} from '@app/lib/models/user';
import {Observable, of} from 'rxjs';
import {filter, map, shareReplay, switchMap, tap} from 'rxjs/operators';

import {isNonNull} from '../lib/preconditions';


interface UserState {
  readonly currentUserName: string|undefined;
  readonly users: {readonly [key: string]: GrrUser};
}

/** ComponentStore implementation for the user store. */
class UserCompoenntStore extends ComponentStore<UserState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({
      currentUserName: undefined,
      users: {},
    });
  }

  private readonly updateUser = this.updater<GrrUser>((state, user) => {
    return {
      currentUserName: user.name,
      users: {
        ...state.users,
        [user.name]: user,
      },
    };
  });

  private readonly fetchCurrentUser = this.effect(
      obs$ => obs$.pipe(
          switchMap(() => this.httpApiService.fetchCurrentUser()),
          map(u => translateGrrUser(u)),
          tap(u => {
            this.updateUser(u);
          }),
          ));

  /** An observable emitting the current user object. */
  readonly currentUser$: Observable<GrrUser> = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.fetchCurrentUser();
      }),
      switchMap(() => this.select(state => {
        if (state.currentUserName) {
          return state.users[state.currentUserName];
        }
        return undefined;
      })),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );
}

/** GlobalStore for user-related logic. */
@Injectable({
  providedIn: 'root',
})
export class UserGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new UserCompoenntStore(this.httpApiService);

  readonly currentUser$ = this.store.currentUser$;
}
