import {TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';

import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {initTestEnvironment} from '../testing';

import {UserGlobalStore} from './user_global_store';

initTestEnvironment();

describe('UserGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let userGlobalStore: UserGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        UserGlobalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false}
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

  it('correctly emits the API result in currentUser$', async () => {
    const promise = firstValueFrom(userGlobalStore.currentUser$);
    httpApiService.mockedObservables.fetchCurrentUser.next({
      username: 'test',
    });
    expect(await promise).toEqual({
      name: 'test',
      canaryMode: false,
      huntApprovalRequired: false,
    });
  });
});
