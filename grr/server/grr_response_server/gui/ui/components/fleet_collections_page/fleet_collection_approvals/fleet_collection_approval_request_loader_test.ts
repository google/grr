import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../../../lib/api/http_api_with_translation_test_util';
import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {
  ApprovalRequestStoreMock,
  newApprovalRequestStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FLEET_COLLECTION_ROUTES} from '../../app/routing';
import {FleetCollectionApprovalRequestLoader} from './fleet_collection_approval_request_loader';

initTestEnvironment();

describe('Fleet Collection Approval Request Loader', () => {
  let approvalRequestStoreMock: ApprovalRequestStoreMock;
  let httpApiServiceMock: HttpApiWithTranslationServiceMock;

  beforeEach(waitForAsync(() => {
    approvalRequestStoreMock = newApprovalRequestStoreMock();
    httpApiServiceMock = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionApprovalRequestLoader,
        NoopAnimationsModule,
        RouterModule.forRoot(FLEET_COLLECTION_ROUTES, {
          bindToComponentInputs: true,
          paramsInheritanceStrategy: 'always',
        }),
      ],
      providers: [
        {
          provide: ApprovalRequestStore,
          useValue: approvalRequestStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiServiceMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('navigation to /fleet-collections/:id/approvals/:id/users/:user triggers fetching of the approval', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();

    await routerTestingHarness.navigateByUrl(
      '/fleet-collections/ABCD1234/approvals/A.1234/users/testuser',
    );

    expect(
      approvalRequestStoreMock.fetchFleetCollectionApproval,
    ).toHaveBeenCalledWith('A.1234', 'ABCD1234', 'testuser');
  }));
});
