import {TestBed} from '@angular/core/testing';
import {Subject} from 'rxjs';

import {ApiClientApproval} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {initTestEnvironment} from '../testing';

import {HomePageGlobalStore} from './home_page_global_store';

initTestEnvironment();

describe('HomePageGlobalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let store: HomePageGlobalStore;
  let apiListRecentClientApprovals$: Subject<ReadonlyArray<ApiClientApproval>>;

  beforeEach(() => {
    apiListRecentClientApprovals$ = new Subject();
    httpApiService = {
      listRecentClientApprovals:
          jasmine.createSpy('listRecentClientApprovals')
              .and.returnValue(apiListRecentClientApprovals$),
    };

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        HomePageGlobalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false}
    });

    store = TestBed.inject(HomePageGlobalStore);
  });

  it('calls the API on subscription to recentClientApprovals$', () => {
    store.recentClientApprovals$.subscribe();
    expect(httpApiService.listRecentClientApprovals).toHaveBeenCalled();
  });

  it('correctly emits the API results in recentClientApprovals$', (done) => {
    store.recentClientApprovals$.subscribe((results) => {
      expect(results.length).toBe(2);
      expect(results[0]).toEqual(jasmine.objectContaining({approvalId: '2'}));
      expect(results[1]).toEqual(jasmine.objectContaining({approvalId: '3'}));
      done();
    });

    apiListRecentClientApprovals$.next([
      {
        subject: {
          clientId: 'C.1234',
          fleetspeakEnabled: false,
          knowledgeBase: {},
          labels: [],
          age: '0',
        },
        id: '2',
        reason: 'Pending reason',
        requestor: 'testuser',
        isValid: false,
        isValidMessage: 'Need at least 1 more approvers.',
        approvers: ['testuser'],
        notifiedUsers: ['b', 'c'],
      },
      {
        subject: {
          clientId: 'C.12345678',
          fleetspeakEnabled: false,
          knowledgeBase: {},
          labels: [],
          age: '0',
        },
        id: '3',
        reason: 'Pending reason',
        requestor: 'testuser',
        isValid: false,
        isValidMessage: 'Need at least 1 more approvers.',
        approvers: ['testuser'],
        notifiedUsers: ['b', 'c'],
      },
    ]);
  });
});
