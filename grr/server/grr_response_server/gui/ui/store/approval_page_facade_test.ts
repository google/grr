import {discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {ConfigService} from '@app/components/config/config';
import {ApiClientApproval} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ApprovalPageFacade} from '@app/store/approval_page_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {ClientApproval} from '../lib/models/client';
import {newClient} from '../lib/models/model_test_util';
import {removeUndefinedKeys} from '../testing';


initTestEnvironment();

describe('ApprovalPageFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let approvalPageFacade: ApprovalPageFacade;
  let configService: ConfigService;
  let apiFetchClientApproval$: Subject<ApiClientApproval>;
  let apiGrantClientApproval$: Subject<ApiClientApproval>;

  beforeEach(() => {
    apiFetchClientApproval$ = new Subject();
    apiGrantClientApproval$ = new Subject();
    httpApiService = {
      fetchClientApproval: jasmine.createSpy('fetchClientApproval')
                               .and.returnValue(apiFetchClientApproval$),
      grantClientApproval: jasmine.createSpy('grantClientApproval')
                               .and.returnValue(apiGrantClientApproval$),
    };

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            ApprovalPageFacade,
            // Apparently, useValue creates a copy of the object. Using
            // useFactory, to make sure the instance is shared.
            {provide: HttpApiService, useFactory: () => httpApiService},
          ],
        })
        .compileComponents();

    approvalPageFacade = TestBed.inject(ApprovalPageFacade);
    configService = TestBed.inject(ConfigService);
  });


  it('emits the approval in approval$', fakeAsync(() => {
       approvalPageFacade.selectApproval(
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
       approvalPageFacade.approval$.subscribe(approval => {
         numCalls++;
         expect(removeUndefinedKeys(approval)).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();


       apiFetchClientApproval$.next({
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
       apiFetchClientApproval$.complete();
       expect(numCalls).toBe(1);
     }));

  it('calls the fetchClientApproval API on approval$ subscription',
     fakeAsync(() => {
       approvalPageFacade.selectApproval(
           {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       approvalPageFacade.approval$.subscribe();

       // This is needed since flow list entries are updated in a timer loop
       // and the first call is scheduled after 0 milliseconds (meaning it
       // will happen right after it was scheduled, but still asynchronously).
       tick(1);
       discardPeriodicTasks();

       expect(httpApiService.fetchClientApproval)
           .toHaveBeenCalledWith(
               {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
     }));

  it('calls the API on grantApproval()', () => {
    approvalPageFacade.selectApproval(
        {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
    approvalPageFacade.grantApproval();

    expect(httpApiService.grantClientApproval)
        .toHaveBeenCalledWith(
            {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
  });

  it('updates approval$ after grantApproval()', fakeAsync(() => {
       approvalPageFacade.selectApproval(
           {clientId: 'C.1234', requestor: 'testuser', approvalId: '123'});
       approvalPageFacade.grantApproval();

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
       approvalPageFacade.approval$.subscribe(approval => {
         numCalls++;
         expect(removeUndefinedKeys(approval)).toEqual(expected);
       });
       tick(1);
       discardPeriodicTasks();

       apiGrantClientApproval$.next({
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
       apiGrantClientApproval$.complete();
       expect(numCalls).toBe(1);
     }));
});
