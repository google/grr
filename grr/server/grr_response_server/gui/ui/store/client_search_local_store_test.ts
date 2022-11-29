import {TestBed} from '@angular/core/testing';
import {Subject} from 'rxjs';

import {HttpApiService} from '../lib/api/http_api_service';
import {injectHttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {latestValueFrom} from '../lib/reactive';
import {initTestEnvironment} from '../testing';

import {ClientSearchLocalStore} from './client_search_local_store';

initTestEnvironment();

describe('ClientSearchLocalStore', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        {provide: HttpApiService, useFactory: mockHttpApiService},
      ],
      teardown: {destroyAfterEach: false}
    });
  });

  it('fetches new search results from API when "searchClients" is called with a non-empty query, and sorts them by when they were last seen',
     async () => {
       const clientSearchLocalStore = TestBed.inject(ClientSearchLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       clientSearchLocalStore.searchClients('sample query');
       const clients = latestValueFrom(clientSearchLocalStore.clients$);

       expect(httpApiService.searchClients)
           .toHaveBeenCalledWith(
               {query: 'sample query', offset: '0', count: '50'});

       httpApiService.mockedObservables.searchClients.next({
         items: [
           {
             clientId: 'C.1234',
             lastSeenAt: '1571789996678000',
             age: '0',
           },
           {
             clientId: 'C.5678',
             lastSeenAt: '1571789996680000',
             age: '0',
           },
         ]
       });

       expect(clients.get()).toEqual([
         jasmine.objectContaining({clientId: 'C.5678'}),
         jasmine.objectContaining({clientId: 'C.1234'}),
       ]);
     });

  it('does not fetch new search results from the API when "searchClients" is called with an empty query',
     async () => {
       const clientSearchLocalStore = TestBed.inject(ClientSearchLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       clientSearchLocalStore.searchClients('');
       const clients = latestValueFrom(clientSearchLocalStore.clients$);

       expect(httpApiService.searchClients).not.toHaveBeenCalled();
       expect(clients.get()).toEqual([]);
     });

  it('returns only fresh results after multiple searches', async () => {
    const clientSearchLocalStore = TestBed.inject(ClientSearchLocalStore);
    const httpApiService = injectHttpApiServiceMock();

    httpApiService.mockedObservables.searchClients = new Subject();

    clientSearchLocalStore.searchClients('sample query');
    const clients = latestValueFrom(clientSearchLocalStore.clients$);

    expect(httpApiService.searchClients)
        .toHaveBeenCalledWith(
            {query: 'sample query', offset: '0', count: '50'});

    httpApiService.mockedObservables.searchClients.next({
      items: [{
        clientId: 'C.1234',
        age: '0',
      }]
    });

    expect(clients.get()).toEqual([jasmine.objectContaining(
        {clientId: 'C.1234'})]);

    httpApiService.mockedObservables.searchClients = new Subject();

    clientSearchLocalStore.searchClients('new query');

    expect(httpApiService.searchClients)
        .toHaveBeenCalledWith({query: 'new query', offset: '0', count: '50'});

    httpApiService.mockedObservables.searchClients.next({
      items: [{
        clientId: 'C.5678',
        age: '0',
      }]
    });

    expect(clients.get()).toEqual([jasmine.objectContaining(
        {clientId: 'C.5678'})]);
  });
});
