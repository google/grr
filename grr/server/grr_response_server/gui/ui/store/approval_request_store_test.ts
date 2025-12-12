import {TestBed} from '@angular/core/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {
  newClientApproval,
  newHuntApproval,
} from '../lib/models/model_test_util';
import {initTestEnvironment} from '../testing';
import {ApprovalRequestStore} from './approval_request_store';

initTestEnvironment();

describe('ApprovalRequestStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        ApprovalRequestStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
      teardown: {destroyAfterEach: true},
    });
  });

  it('stores the requested approval in the store when fetchClientApproval is called', () => {
    const store = TestBed.inject(ApprovalRequestStore);

    store.fetchClientApproval('A.1234', 'C.1234', 'testuser');
    const approval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'pending', reason: 'Need 1 more approver'},
      requestor: 'testuser',
      approvalId: 'A.1234',
    });
    httpApiService.mockedObservables.fetchClientApproval.next(approval);

    expect(store.requestedClientApproval()).toEqual(approval);
  });

  it('calls api to grantClientApproval when grantClientApproval() is called and updates store', () => {
    const store = TestBed.inject(ApprovalRequestStore);

    store.grantClientApproval(
      newClientApproval({
        clientId: 'C.1234',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        requestor: 'testuser',
        approvalId: 'A.1234',
      }),
    );
    const grantedApproval = newClientApproval({
      clientId: 'C.1234',
      status: {type: 'valid'},
      requestor: 'testuser',
      approvalId: 'A.1234',
      approvers: ['approver'],
    });
    httpApiService.mockedObservables.grantClientApproval.next(grantedApproval);

    expect(httpApiService.grantClientApproval).toHaveBeenCalledWith({
      clientId: 'C.1234',
      requestor: 'testuser',
      approvalId: 'A.1234',
    });
    expect(store.requestedClientApproval()).toEqual(grantedApproval);
  });

  it('stores the requested fleet collection approval in the store when fetchFleetCollectionApproval is called', () => {
    const store = TestBed.inject(ApprovalRequestStore);

    store.fetchFleetCollectionApproval('A.1234', 'ABCD1234', 'testuser');
    const approval = newHuntApproval({
      huntId: 'ABCD1234',
      status: {type: 'pending', reason: 'Need 1 more approver'},
      requestor: 'testuser',
      approvalId: 'A.1234',
    });
    httpApiService.mockedObservables.fetchHuntApproval.next(approval);

    expect(store.requestedFleetCollectionApproval()).toEqual(approval);
  });

  it('calls api to grantFleetCollectionApproval when grantFleetCollectionApproval() is called and updates store', () => {
    const store = TestBed.inject(ApprovalRequestStore);

    store.grantFleetCollectionApproval(
      newHuntApproval({
        huntId: 'ABCD1234',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        requestor: 'testuser',
        approvalId: 'A.1234',
      }),
    );
    const grantedApproval = newHuntApproval({
      huntId: 'ABCD1234',
      status: {type: 'valid'},
      requestor: 'testuser',
      approvalId: 'A.1234',
      approvers: ['approver'],
    });
    httpApiService.mockedObservables.grantHuntApproval.next(grantedApproval);

    expect(httpApiService.grantHuntApproval).toHaveBeenCalledWith({
      huntId: 'ABCD1234',
      requestor: 'testuser',
      approvalId: 'A.1234',
    });
    expect(store.requestedFleetCollectionApproval()).toEqual(grantedApproval);
  });
});
