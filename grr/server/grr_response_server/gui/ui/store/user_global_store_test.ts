import {TestBed} from '@angular/core/testing';
import {ApiGrrUser} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {UserGlobalStore} from '@app/store/user_global_store';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

initTestEnvironment();

describe('UserGlobalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let userGlobalStore: UserGlobalStore;
  let apiFetchCurrentUser$: Subject<ApiGrrUser>;

  beforeEach(() => {
    apiFetchCurrentUser$ = new Subject();
    httpApiService = {
      fetchCurrentUser: jasmine.createSpy('fetchCurrentUser')
                            .and.returnValue(apiFetchCurrentUser$),
    };

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        UserGlobalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
    });

    userGlobalStore = TestBed.inject(UserGlobalStore);
  });

  it('does not call the API without subscription', () => {
    expect(httpApiService.fetchCurrentUser).not.toHaveBeenCalled();
  });

  it('calls the API on first currentUser subscription', () => {
    userGlobalStore.currentUser$.subscribe();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalled();
  });

  it('does not call the API on second currentUser subscription', () => {
    userGlobalStore.currentUser$.subscribe();
    userGlobalStore.currentUser$.subscribe();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalledTimes(1);
  });

  it('correctly emits the API result in currentUser$', (done) => {
    userGlobalStore.currentUser$.subscribe((user) => {
      expect(user).toEqual({
        name: 'test',
      });
      done();
    });
    apiFetchCurrentUser$.next({
      username: 'test',
    });
  });
});
