import {TestBed} from '@angular/core/testing';
import {Subject} from 'rxjs';

import {ApiClient} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {newClient} from '../lib/models/model_test_util';
import {initTestEnvironment} from '../testing';

import {getClientVersions} from './client_details_diff';
import {ClientDetailsGlobalStore} from './client_details_global_store';


initTestEnvironment();

describe('ClientDetailsGlobalStore', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientDetailsGlobalStore: ClientDetailsGlobalStore;
  let apiFetchClientVersions$: Subject<ReadonlyArray<ApiClient>>;

  beforeEach(() => {
    apiFetchClientVersions$ = new Subject();
    httpApiService = {
      fetchClientVersions: jasmine.createSpy('fetchClientVersions')
                               .and.returnValue(apiFetchClientVersions$)
    };

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ClientDetailsGlobalStore,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    clientDetailsGlobalStore = TestBed.inject(ClientDetailsGlobalStore);
    clientDetailsGlobalStore.selectClient('C.1234');
  });

  it('fetches client versions from API when "selectClient" is called', () => {
    expect(httpApiService.fetchClientVersions).toHaveBeenCalledWith('C.1234');

    clientDetailsGlobalStore.selectClient('C.4321');
    expect(httpApiService.fetchClientVersions).toHaveBeenCalledWith('C.4321');
  });

  it('updates store\'s state clientVersions on selectClient call', (done) => {
    apiFetchClientVersions$.next([
      {
        clientId: 'C.1234',
        memorySize: '1',
        age: '1580515200000',
      },
      {
        clientId: 'C.1234',
        memorySize: '123',
        age: '1583020800000',
      },
    ]);

    clientDetailsGlobalStore.selectedClientVersions$.subscribe((versions) => {
      expect(versions.length).toEqual(2);
      done();
    });
  });

  it('updates store\'s state clientEntriesChanged on selectClient call',
     (done) => {
       apiFetchClientVersions$.next([
         {
           clientId: 'C.1234',
           memorySize: '1',
           age: '1580515200000',
         },
         {
           clientId: 'C.1234',
           memorySize: '123',
           age: '1583020800000',
         },
       ]);

       clientDetailsGlobalStore.selectedClientEntriesChanged$.subscribe(
           (clientEntriesChanged) => {
             expect(clientEntriesChanged).toBeTruthy();
             done();
           });
     });

  it('getClientVersions() correctly translates snapshots into client changes',
     () => {
       const snapshots = [
         // Client first seen
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
           changes: ['Client first seen'],
         },
         {
           client: snapshots[1],
           changes: ['3 User entries added'],
         },
         {
           client: snapshots[2],
           changes:
               ['2 User full name entries added', 'User home directory added'],
         },
         {
           client: snapshots[3],
           changes: ['User home directory updated', 'User added'],
         },
         {
           client: snapshots[4],
           changes: ['4 User entries deleted'],
         },
         {
           client: snapshots[5],
           changes: [],
         },
         {
           client: snapshots[6],
           changes: ['Network interface added'],
         },
         {
           client: snapshots[7],
           changes: ['Network address added', 'IP address updated'],
         },
         {
           client: snapshots[8],
           changes: ['5 new changes'],
         },
       ].reverse();

       const clientChanges = getClientVersions(snapshots.reverse());

       expect(clientChanges.map(
                  change => [change.client, [...change.changes].sort()]))
           .toEqual(expectedClientChanges.map(
               expectedChange =>
                   [expectedChange.client, expectedChange.changes.sort()]));
     });

  it('getClientVersions() includes snapshots without changes', () => {
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
        client: snapshots[0],
        changes: [],
      },
      {
        client: snapshots[1],
        changes: ['Client first seen'],
      },
    ];

    const clientChanges = getClientVersions(snapshots);
    expect(clientChanges).toEqual(expectedClientChanges);
  });
});
