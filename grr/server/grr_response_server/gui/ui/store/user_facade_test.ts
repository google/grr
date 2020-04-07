import {TestBed} from '@angular/core/testing';
import {ApiGrrUser} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {GrrStoreModule} from '@app/store/store_module';
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
      imports: [
        GrrStoreModule,
      ],
      providers: [
        UserFacade,
        {provide: HttpApiService, useValue: httpApiService},
      ],
    });

    userFacade = TestBed.inject(UserFacade);
  });

  it('calls the API on fetchCurrentUser', () => {
    userFacade.fetchCurrentUser();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalled();
  });

  it('correctly emits the API result in currentUser$', (done) => {
    userFacade.fetchCurrentUser();
    apiFetchCurrentUser$.next({
      username: 'test',
    });
    userFacade.currentUser$.subscribe((user) => {
      expect(user).toEqual({
        name: 'test',
      });
      done();
    });
  });
});
