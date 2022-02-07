import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';

import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {RequestStatusType} from '../lib/api/track_request';
import {ClientApproval} from '../lib/models/client';
import {newClient} from '../lib/models/model_test_util';
import {initTestEnvironment, removeUndefinedKeys} from '../testing';

import {ApprovalPageGlobalStore} from './approval_page_global_store';


initTestEnvironment();

describe('ApprovalPageGlobalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let approvalPageGlobalStore: ApprovalPageGlobalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ApprovalPageGlobalStore,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    approvalPageGlobalStore = TestBed.inject(ApprovalPageGlobalStore);
  });


  it('emits the approval in approval$', fakeAsync(() => {
       approvalPageGlobalStore.selectApproval(
           {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});

       const expected: ClientApproval = {
         status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
         reason: 'Pending reason',
         requestor: 'testuser',
         clientId: 'C.1234',
         approvalId: '123',
         requestedApprovers: ['b', 'c'],
         approvers: [],
         subject: newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
           knowledgeBase: {},
           labels: [],
           age: new Date(0),
         }),
       };

       let numCalls = 0;
       approvalPageGlobalStore.approval$.subscribe(approval => {
         numCalls++;
         expect(removeUndefinedKeys(approval)).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();


       httpApiService.mockedObservables.subscribeToClientApproval.next({
         subject: {
           clientId: 'C.1234',
           fleetspeakEnabled: false,
           knowledgeBase: {},
           labels: [],
           age: '0',
         },
         id: '123',
         reason: 'Pending reason',
         requestor: 'testuser',
         isValid: false,
         isValidMessage: 'Need at least 1 more approvers.',
         approvers: ['testuser'],
         notifiedUsers: ['b', 'c'],
       });
       httpApiService.mockedObservables.subscribeToClientApproval.complete();
       expect(numCalls).toBe(1);
     }));

  it('calls the subscribeToClientApproval API on approval$ subscription',
     fakeAsync(() => {
       approvalPageGlobalStore.selectApproval(
           {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       approvalPageGlobalStore.approval$.subscribe();

       // This is needed since flow list entries are updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.subscribeToClientApproval)
           .toHaveBeenCalledWith(
               {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
     }));

  it('calls the API on grantApproval()', async () => {
    approvalPageGlobalStore.selectApproval(
        {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
    approvalPageGlobalStore.grantApproval();

    expect(httpApiService.grantClientApproval)
        .toHaveBeenCalledWith(
            {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
    expect(await firstValueFrom(approvalPageGlobalStore.grantRequestStatus$))
        .toEqual({status: RequestStatusType.SENT});
  });

  it('updates approval$ after grantApproval()', fakeAsync(() => {
       approvalPageGlobalStore.selectApproval(
           {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       approvalPageGlobalStore.grantApproval();

       const expected: ClientApproval = {
         status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
         reason: 'Pending reason',
         requestor: 'testuser',
         clientId: 'C.1234',
         approvalId: '123',
         requestedApprovers: ['b', 'c'],
         approvers: ['b'],
         subject: newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: false,
           knowledgeBase: {},
           labels: [],
           age: new Date(0),
         }),
       };

       let numCalls = 0;
       approvalPageGlobalStore.approval$.subscribe(approval => {
         numCalls++;
         expect(removeUndefinedKeys(approval)).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();

       httpApiService.mockedObservables.grantClientApproval.next({
         subject: {
           clientId: 'C.1234',
           fleetspeakEnabled: false,
           knowledgeBase: {},
           labels: [],
           age: '0',
         },
         id: '123',
         reason: 'Pending reason',
         requestor: 'testuser',
         isValid: false,
         isValidMessage: 'Need at least 1 more approvers.',
         approvers: ['testuser', 'b'],
         notifiedUsers: ['b', 'c'],
       });
       httpApiService.mockedObservables.grantClientApproval.complete();
       expect(numCalls).toBe(1);
     }));
});
