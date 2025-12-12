import {TestBed} from '@angular/core/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {newClient, newClientApproval} from '../lib/models/model_test_util';
import {ClientSearchStore} from './client_search_store';

describe('Client Search Store', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        ClientSearchStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
    });
  });

  it('calls api to search clients and updates store', () => {
    const store = TestBed.inject(ClientSearchStore);

    store.searchClients('C.123456789');
    const clients = [
      newClient({clientId: 'C.1234567890'}),
      newClient({clientId: 'C.1234567891'}),
      newClient({clientId: 'C.1234567892'}),
    ];
    httpApiService.mockedObservables.searchClients.next(clients);

    expect(httpApiService.searchClients).toHaveBeenCalledWith({
      query: 'C.123456789',
      count: '256',
      offset: '0',
    });
    expect(store.clients()).toEqual(clients);
  });

  it('does not call api to search clients when query is empty', () => {
    const store = TestBed.inject(ClientSearchStore);

    store.searchClients('');

    expect(httpApiService.searchClients).not.toHaveBeenCalled();
  });

  it('calls api to fetch recent clients and updates store', () => {
    const store = TestBed.inject(ClientSearchStore);

    store.fetchRecentClientApprovals();
    const approvals = [
      newClientApproval({clientId: 'C.1234567890'}),
      newClientApproval({clientId: 'C.1234567891'}),
      newClientApproval({clientId: 'C.1234567892'}),
    ];
    httpApiService.mockedObservables.listRecentClientApprovals.next(approvals);

    expect(httpApiService.listRecentClientApprovals).toHaveBeenCalledWith({
      count: 20,
    });
    expect(store.recentApprovals()).toEqual(approvals);
  });
});
