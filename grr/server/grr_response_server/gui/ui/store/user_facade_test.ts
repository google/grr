import {TestBed} from '@angular/core/testing';
import {ApiGrrUser} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {UserFacade} from '@app/store/user_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

initTestEnvironment();

describe('UserFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let userFacade: UserFacade;
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
        UserFacade,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
    });

    userFacade = TestBed.inject(UserFacade);
  });

  it('does not call the API without subscription', () => {
    expect(httpApiService.fetchCurrentUser).not.toHaveBeenCalled();
  });

  it('calls the API on first currentUser subscription', () => {
    userFacade.currentUser$.subscribe();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalled();
  });

  it('does not call the API on second currentUser subscription', () => {
    userFacade.currentUser$.subscribe();
    userFacade.currentUser$.subscribe();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalledTimes(1);
  });

  it('correctly emits the API result in currentUser$', (done) => {
    userFacade.currentUser$.subscribe((user) => {
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
