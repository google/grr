import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClient} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {ClientDetailsFacade} from './client_details_facade';


initTestEnvironment();

describe('ClientDetailsFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientDetailsFacade: ClientDetailsFacade;
  let configService: ConfigService;
  let apiFetchClient$: Subject<ApiClient>;
  let apiFetchClientVersions$: Subject<ReadonlyArray<ApiClient>>;

  beforeEach(() => {
    apiFetchClient$ = new Subject();
    apiFetchClientVersions$ = new Subject();
    httpApiService = {
      fetchClient:
          jasmine.createSpy('fetchClient').and.returnValue(apiFetchClient$),
      fetchClientVersions: jasmine.createSpy('fetchClientVersions')
                               .and.returnValue(apiFetchClientVersions$)
    };

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ClientDetailsFacade,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
        })
        .compileComponents();

    clientDetailsFacade = TestBed.inject(ClientDetailsFacade);
    configService = TestBed.inject(ConfigService);

    clientDetailsFacade.selectClient('C.1234');
    apiFetchClient$.next({
      clientId: 'C.1234',
    });
  });


  it('fetches client data only after selectedClient$ is subscribed to',
     fakeAsync(() => {
       expect(httpApiService.fetchClient).not.toHaveBeenCalled();
       clientDetailsFacade.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();
       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');
     }));

  it('polls and updates selectedClient$ periodically', fakeAsync(() => {
       clientDetailsFacade.selectedClient$.subscribe();

       tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       // First call happens at 0, next one at selectedClientPollingIntervalMs
       // and the next one at selectedClientPollingIntervalMs * 2.
       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(3);
     }));

  it('polls and updates selectedClient$ when another client is selected',
     fakeAsync(() => {
       clientDetailsFacade.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.1234');

       clientDetailsFacade.selectClient('C.5678');
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.fetchClient).toHaveBeenCalledWith('C.5678');
     }));

  it('stops updating selectedClient$ when unsubscribed from it',
     fakeAsync(() => {
       const subscribtion = clientDetailsFacade.selectedClient$.subscribe();

       // This is needed since selected client is updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);

       subscribtion.unsubscribe();
       // Fast forward for another 2 polling intervals, to check if
       // the client is still fetched or not after unsubscribe.
       // The number of calls to fetchClient() should stay the same
       tick(configService.config.selectedClientPollingIntervalMs * 2 + 1);
       discardPeriodicTasks();

       expect(httpApiService.fetchClient).toHaveBeenCalledTimes(1);
     }));

  it('updates selectedClient$ with changed client data when underlying API client data changes.',
     fakeAsync((done: DoneFn) => {
       const expectedClients: Client[] = [
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
         }),
         newClient({
           clientId: 'C.5678',
           fleetspeakEnabled: true,
         }),
       ];

       apiFetchClient$.next({
         clientId: 'C.5678',
         fleetspeakEnabled: true,
       })

       let i = 0;
       clientDetailsFacade.selectedClient$.subscribe(client => {
         expect(client).toEqual(expectedClients[i]);
         i++;
         if (i === expectedClients.length) {
           done();
         }
       });

       tick(
           configService.config.selectedClientPollingIntervalMs *
               (expectedClients.length - 1) +
           1);
       discardPeriodicTasks();
     }));

  it('fetches client versions from API when selectedClientVersions$ is subscribed to',
     () => {
       expect(httpApiService.fetchClientVersions).not.toHaveBeenCalled();
       clientDetailsFacade.selectedClientSnapshots$.subscribe();

       expect(httpApiService.fetchClientVersions)
           .toHaveBeenCalledWith('C.1234');
     });

  it('emits an array of Client objects through selectedClientVersions$',
     fakeAsync((done: DoneFn) => {
       apiFetchClientVersions$.next([
         {
           clientId: 'C.1234',
           fleetspeakEnabled: true,
         },
         {
           clientId: 'C.1234',
           fleetspeakEnabled: false,
         },
       ]);

       const expectedClientVersions = [
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: true,
         }),
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
         }),
       ];

       clientDetailsFacade.selectedClientSnapshots$.subscribe(clientVersions => {
         expect(clientVersions).toEqual(expectedClientVersions);
         done();
       });

       tick(1);
     }));
});
