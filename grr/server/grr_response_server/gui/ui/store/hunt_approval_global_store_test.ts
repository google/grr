import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiHuntState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {translateHuntApproval} from '../lib/api_translation/hunt';
import {HuntApproval} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment, removeUndefinedKeys} from '../testing';

import {HuntApprovalGlobalStore} from './hunt_approval_global_store';
import {UserGlobalStore} from './user_global_store';
import {mockUserGlobalStore, UserGlobalStoreMock} from './user_global_store_test_util';

initTestEnvironment();


describe('HuntApprovalGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let userGlobalStore: UserGlobalStoreMock;
  let huntApprovalGlobalStore: HuntApprovalGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    userGlobalStore = mockUserGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntApprovalGlobalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: UserGlobalStore, useFactory: () => userGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntApprovalGlobalStore = TestBed.inject(HuntApprovalGlobalStore);
  });

  it('emits latest pending approval in latestApproval$', fakeAsync(async () => {
       const expected: HuntApproval = translateHuntApproval({
         subject: {
           huntId: 'hunt_1234',
           creator: 'creator',
           name: 'name',
           state: ApiHuntState.PAUSED,
           created: '12345',
           huntRunnerArgs: {clientRate: 0},
           flowArgs: {},
           flowName: 'name',
         },
         id: '2',
         reason: 'Pending reason',
         requestor: 'requestor',
         isValid: false,
         isValidMessage: 'Need at least 1 more approvers.',
         approvers: ['approver'],
         notifiedUsers: ['b', 'c'],
       });

       const promise = firstValueFrom(
           huntApprovalGlobalStore.latestApproval$.pipe(filter(isNonNull)));
       huntApprovalGlobalStore.selectHunt('hunt_1234');

       httpApiService.mockedObservables.subscribeToListHuntApprovals.next([
         {
           subject: {
             huntId: 'hunt_1234',
             creator: 'creator',
             name: 'name',
             state: ApiHuntState.PAUSED,
             created: '12345',
             huntRunnerArgs: {clientRate: 0},
             flowArgs: {},
             flowName: 'wrong name',
           },
           id: '1',
           reason: 'Old reason',
           requestor: 'requestor',
           isValid: false,
           isValidMessage: 'Approval request is expired.',
           approvers: ['approver'],
           notifiedUsers: ['b', 'c'],
         },
         {
           subject: {
             huntId: 'hunt_1234',
             creator: 'creator',
             name: 'name',
             state: ApiHuntState.PAUSED,
             created: '12345',
             huntRunnerArgs: {clientRate: 0},
             flowArgs: {},
             flowName: 'name',
           },
           id: '2',
           reason: 'Pending reason',
           requestor: 'requestor',
           isValid: false,
           isValidMessage: 'Need at least 1 more approvers.',
           approvers: ['approver'],
           notifiedUsers: ['b', 'c'],
         },
       ]);

       expect(httpApiService.subscribeToListHuntApprovals)
           .toHaveBeenCalledWith('hunt_1234');
       expect(removeUndefinedKeys(await promise))
           .toEqual(removeUndefinedKeys(expected));
     }));

  it('emits huntApprovalRoute$ based on latest approval',
     fakeAsync(async () => {
       const expected =
           ['hunts', 'hunt_1234', 'users', 'requestor', 'approvals', '2'];

       const promise =
           firstValueFrom(huntApprovalGlobalStore.huntApprovalRoute$.pipe(
               filter(v => v.length > 0)));
       huntApprovalGlobalStore.selectHunt('hunt_1234');

       httpApiService.mockedObservables.subscribeToListHuntApprovals.next([
         {
           subject: {
             huntId: 'hunt_1234',
             creator: 'creator',
             name: 'name',
             state: ApiHuntState.PAUSED,
             created: '12345',
             huntRunnerArgs: {clientRate: 0},
             flowArgs: {},
             flowName: 'name',
           },
           id: '2',
           reason: 'Pending reason',
           requestor: 'requestor',
           isValid: false,
           isValidMessage: 'Need at least 1 more approvers.',
           approvers: ['approver'],
           notifiedUsers: ['b', 'c'],
         },
       ]);

       expect(httpApiService.subscribeToListHuntApprovals)
           .toHaveBeenCalledWith('hunt_1234');
       expect(removeUndefinedKeys(await promise))
           .toEqual(removeUndefinedKeys(expected));
     }));

  it('emits verified access in hasAccess$', fakeAsync(async () => {
       const promise = firstValueFrom(
           huntApprovalGlobalStore.hasAccess$.pipe(filter(isNonNull)));
       huntApprovalGlobalStore.selectHunt('hunt_1234');

       httpApiService.mockedObservables.subscribeToVerifyHuntAccess.next(true);

       expect(httpApiService.subscribeToVerifyHuntAccess)
           .toHaveBeenCalledWith('hunt_1234');
       expect(await promise).toBeTrue();
     }));

  it('emits user huntApprovalRequired$ - false', fakeAsync(async () => {
       const promise =
           firstValueFrom(huntApprovalGlobalStore.huntApprovalRequired$.pipe(
               filter(isNonNull)));
       userGlobalStore.mockedObservables.currentUser$.next(
           {name: 'testuser', canaryMode: false, huntApprovalRequired: false});
       expect(await promise).toBeFalse();
     }));

  it('emits user huntApprovalRequired$ - true', fakeAsync(async () => {
       const promise =
           firstValueFrom(huntApprovalGlobalStore.huntApprovalRequired$.pipe(
               filter(isNonNull)));
       userGlobalStore.mockedObservables.currentUser$.next(
           {name: 'testuser', canaryMode: true, huntApprovalRequired: true});
       expect(await promise).toBeTrue();
     }));

  it('calls request hunt approval', fakeAsync(() => {
       huntApprovalGlobalStore.requestHuntApproval({
         huntId: 'hunt_1234',
         approvers: ['jake'],
         reason: 'sample reason',
         cc: [],
       });
       expect(httpApiService.requestHuntApproval).toHaveBeenCalledWith({
         huntId: 'hunt_1234',
         approvers: ['jake'],
         reason: 'sample reason',
         cc: [],
       });
     }));
});
