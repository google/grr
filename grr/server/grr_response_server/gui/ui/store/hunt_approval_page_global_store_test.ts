import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';

import {ApiHuntState} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {RequestStatusType} from '../lib/api/track_request';
import {initTestEnvironment} from '../testing';

import {HuntApprovalPageGlobalStore} from './hunt_approval_page_global_store';


initTestEnvironment();

describe('ApprovalPageGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let huntApprovalPageGlobalStore: HuntApprovalPageGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            HuntApprovalPageGlobalStore,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    huntApprovalPageGlobalStore = TestBed.inject(HuntApprovalPageGlobalStore);
  });


  it('emits the hunt approval in approval$', fakeAsync(() => {
       huntApprovalPageGlobalStore.selectHuntApproval(
           {huntId: 'C.1234', approvalId: '123', requestor: 'testuser'});

       const expected = jasmine.objectContaining({
         approvalId: '123',
         huntId: 'C.1234',
         requestor: 'testuser',
         reason: 'very important reason',
         status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
         requestedApprovers: ['b', 'c'],
         approvers: [],
         subject: jasmine.objectContaining({
           creator: 'buster',
           description: '',
           huntId: 'C.1234',
           name: 'get_free_bitcoin',
           created: new Date(123456789 / 1000),
         }),
       });

       let numCalls = 0;
       huntApprovalPageGlobalStore.approval$.subscribe(approval => {
         numCalls++;
         expect(approval).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();

       httpApiService.mockedObservables.subscribeToHuntApproval.next({
         id: '123',
         requestor: 'testuser',
         reason: 'very important reason',
         isValid: false,
         isValidMessage: 'Need at least 1 more approvers.',
         notifiedUsers: ['b', 'c'],
         approvers: ['testuser'],
         subject: {
           creator: 'buster',
           description: '',
           huntId: 'C.1234',
           name: 'get_free_bitcoin',
           created: '123456789',
           state: ApiHuntState.STARTED,
           huntRunnerArgs: {clientRate: 10},
         },
       });
       httpApiService.mockedObservables.subscribeToHuntApproval.complete();
       expect(numCalls).toBe(1);
     }));

  it('calls the subscribeToHuntApproval API on approval$ subscription',
     fakeAsync(() => {
       huntApprovalPageGlobalStore.selectHuntApproval(
           {huntId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       huntApprovalPageGlobalStore.approval$.subscribe();

       // This is needed since selected hunt approval is updated in a timer
       // loop and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.subscribeToHuntApproval)
           .toHaveBeenCalledWith(
               {huntId: 'C.1234', approvalId: '123', requestor: 'testuser'});
     }));

  it('calls the API on grantApproval()', async () => {
    huntApprovalPageGlobalStore.selectHuntApproval(
        {huntId: 'C.1234', requestor: 'testuser', approvalId: '123'});
    huntApprovalPageGlobalStore.grantApproval();

    expect(httpApiService.grantHuntApproval)
        .toHaveBeenCalledWith(
            {huntId: 'C.1234', requestor: 'testuser', approvalId: '123'});
    expect(
        await firstValueFrom(huntApprovalPageGlobalStore.grantRequestStatus$))
        .toEqual({status: RequestStatusType.SENT});
  });

  it('updates approval$ after grantApproval()', fakeAsync(() => {
       huntApprovalPageGlobalStore.selectHuntApproval(
           {huntId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       huntApprovalPageGlobalStore.grantApproval();

       const expected = jasmine.objectContaining({
         status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
         reason: 'Pending reason',
         requestor: 'testuser',
         huntId: 'C.1234',
         approvalId: '123',
         requestedApprovers: ['b', 'c'],
         approvers: ['b'],
         subject: jasmine.objectContaining({
           creator: 'buster',
           description: '',
           huntId: 'C.1234',
           name: 'get_free_bitcoin',
           created: new Date(123456789 / 1000),
         }),
       });

       let numCalls = 0;
       huntApprovalPageGlobalStore.approval$.subscribe(approval => {
         numCalls++;
         expect(approval).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();

       httpApiService.mockedObservables.grantHuntApproval.next({
         subject: {
           creator: 'buster',
           description: '',
           huntId: 'C.1234',
           name: 'get_free_bitcoin',
           created: '123456789',
           state: ApiHuntState.STARTED,
           huntRunnerArgs: {clientRate: 10},
         },
         id: '123',
         reason: 'Pending reason',
         requestor: 'testuser',
         isValid: false,
         isValidMessage: 'Need at least 1 more approvers.',
         approvers: ['testuser', 'b'],
         notifiedUsers: ['b', 'c'],
       });
       httpApiService.mockedObservables.grantHuntApproval.complete();
       expect(numCalls).toBe(1);
     }));
});
