import {TestBed} from '@angular/core/testing';
import {ApiSearchClientResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ClientSearchFacade} from '@app/store/client_search_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';
import {skip} from 'rxjs/operators';

initTestEnvironment();

describe('ClientSearchFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientSearchFacade: ClientSearchFacade;
  let apiSearchClients$: Subject<ApiSearchClientResult>;

  beforeEach(() => {
    apiSearchClients$ = new Subject();

    httpApiService = {
      searchClients:
          jasmine.createSpy('searchClients').and.returnValue(apiSearchClients$),
    };

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        ClientSearchFacade,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
    });

    clientSearchFacade = TestBed.inject(ClientSearchFacade);
  });

  it('fetches new search results from API when "searchClients" is called with a non-empty query, and sorts them by when they were last seen',
     (done) => {
       clientSearchFacade.searchClients('sample query');
       expect(httpApiService.searchClients)
           .toHaveBeenCalledWith(
               {query: 'sample query', offset: 0, count: 100});

       const expectedClientIds = ['C.5678', 'C.1234'];
       clientSearchFacade.clients$.pipe(skip(1)).subscribe((results) => {
         expect(results.map(c => c.clientId)).toEqual(expectedClientIds);
         done();
       });

       apiSearchClients$.next({
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
     });

  it('does not fetch new search results from the API when "searchClients" is called with an empty query',
     (done) => {
       clientSearchFacade.clients$.pipe(skip(1)).subscribe((results) => {
         expect(results).toEqual([]);
         done();
       });

       clientSearchFacade.searchClients('');
       expect(httpApiService.searchClients).not.toHaveBeenCalled();
     });

  it('returns only fresh results after multiple searches', (done) => {
    clientSearchFacade.searchClients('sample query');
    expect(httpApiService.searchClients)
        .toHaveBeenCalledWith({query: 'sample query', offset: 0, count: 100});

    clientSearchFacade.searchClients('new query');
    expect(httpApiService.searchClients)
        .toHaveBeenCalledWith({query: 'new query', offset: 0, count: 100});

    const expectedClientIds = ['C.5678'];

    // Only listen to response from second search query.
    clientSearchFacade.clients$.pipe(skip(2)).subscribe((results) => {
      expect(results.map(c => c.clientId)).toEqual(expectedClientIds);
      done();
    });

    // First search response (to 'sample query').
    apiSearchClients$.next({
      items: [{
        clientId: 'C.1234',
        age: '0',
      }]
    });
    // Second search response (to 'new query').
    apiSearchClients$.next({
      items: [{
        clientId: 'C.5678',
        age: '0',
      }]
    });
  });
});
