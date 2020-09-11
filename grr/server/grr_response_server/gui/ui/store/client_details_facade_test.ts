import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClient} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {getClientVersions} from './client_details_diff';
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

       clientDetailsFacade.selectedClientSnapshots$.subscribe(
           clientVersions => {
             expect(clientVersions).toEqual(expectedClientVersions);
             done();
           });

       tick(1);
     }));

  it('getClientVersions() correctly translates snapshots into client changes',
     () => {
       const snapshots = [
         // Client created
         newClient({
           clientId: 'C.1234',
           age: new Date(2020, 1, 1),
         }),
         // 3 User entries added
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1'},
             {username: 'newUser2'},
             {username: 'newUser3'},
           ],
           age: new Date(2020, 1, 2),
         }),
         // Oner User full name updated, One User home directory updated
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1', fullName: 'new User1 fullname'},
             {username: 'newUser2', homedir: 'homedir2'},
             {username: 'newUser3', fullName: 'new User3 fullname'},
           ],
           age: new Date(2020, 1, 3),
         }),
         // One User added, One User home directory updated
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1', fullName: 'new User1 fullname'},
             {username: 'newUser2', homedir: 'homedir2-change'},
             {username: 'newUser3', fullName: 'new User3 fullname'},
             {username: 'newUser4', fullName: 'new User4 fullname'},
           ],
           age: new Date(2020, 1, 4),
         }),
         // 4 User entries deleted
         newClient({
           clientId: 'C.1234',
           users: [],
           age: new Date(2020, 1, 5),
         }),
         // No changes besides non-relevant properties (e.g. age)
         newClient({
           clientId: 'C.1234',
           users: [],
           age: new Date(2020, 1, 6),
         }),
         // One Network interface added
         newClient({
           clientId: 'C.1234',
           users: [],
           networkInterfaces: [
             {
               interfaceName: 'lo',
               macAddress: '',
               addresses: [
                 {
                   addressType: 'IPv4',
                   ipAddress: '1.2.3.4',
                 },
               ],
             },
           ],
           age: new Date(2020, 1, 7),
         }),
         // One IP address added, One IP address updated
         newClient({
           clientId: 'C.1234',
           users: [],
           networkInterfaces: [
             {
               interfaceName: 'lo',
               macAddress: '',
               addresses: [
                 {
                   addressType: 'IPv4',
                   ipAddress: '1.2.3.40',
                 },
                 {
                   addressType: 'IPv4',
                   ipAddress: '127.0.0.1',
                 },
               ],
             },
           ],
           age: new Date(2020, 1, 7),
         }),
         // More than 3 changes => X new changes
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'foo'},
           ],
           memorySize: BigInt(123),
           agentInfo: {
             clientName: 'GRR',
           },
           osInfo: {
             system: 'linux',
           },
           age: new Date(2020, 1, 8),
         }),
       ];

       const expectedClientChanges = [
         {
           client: snapshots[0],
           changes: ['Client created'],
         },
         {
           client: snapshots[1],
           changes: ['3 User entries added'],
         },
         {
           client: snapshots[2],
           changes: [
             '2 User full name entries added', 'One User home directory added'
           ],
         },
         {
           client: snapshots[3],
           changes: ['One User home directory updated', 'One User added'],
         },
         {
           client: snapshots[4],
           changes: ['4 User entries deleted'],
         },
         // Next snapshot is identical to the one before, so it is skipped
         {
           client: snapshots[6],
           changes: ['One Network interface added'],
         },
         {
           client: snapshots[7],
           changes: ['One Network address added', 'One IP address updated'],
         },
         {
           client: snapshots[8],
           changes: ['5 new changes'],
         },
       ].reverse();

       const clientChanges = getClientVersions(snapshots.reverse());

       expect(clientChanges.map(
                  change => {change.client, [...change.changes].sort()}))
           .toEqual(expectedClientChanges.map(expectedChange => {
             expectedChange.client,
             expectedChange.changes.sort()
           }));
     });

  it('getClientVersions() reduces sequences of identical snapshots to the oldest snapshot',
     () => {
       const snapshots = [
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: true,
           age: new Date(2020, 2, 2),
         }),
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: true,
           age: new Date(2020, 1, 1),
         })
       ];

       const expectedClientChanges = [
         {
           client: snapshots[1],
           changes: ['Client created'],
         },
       ];

       const clientChanges = getClientVersions(snapshots);
       expect(clientChanges).toEqual(expectedClientChanges);
     });
});
