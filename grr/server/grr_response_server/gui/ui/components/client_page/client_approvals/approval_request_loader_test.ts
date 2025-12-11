import {signal} from '@angular/core';
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
import {ClientStore} from '../../../store/client_store';
import {
  ApprovalRequestStoreMock,
  ClientStoreMock,
  newApprovalRequestStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {ApprovalRequestLoader} from './approval_request_loader';

initTestEnvironment();

describe('Approval Request Loader', () => {
  let clientStoreMock: ClientStoreMock;
  let approvalRequestStoreMock: ApprovalRequestStoreMock;
  let httpApiServiceMock: HttpApiWithTranslationServiceMock;

  beforeEach(waitForAsync(() => {
    approvalRequestStoreMock = newApprovalRequestStoreMock();
    clientStoreMock = newClientStoreMock();
    httpApiServiceMock = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      imports: [
        ApprovalRequestLoader,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
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

  it('navigation to /approvals/:id/users/:user triggers fetching of the approval', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    const routerTestingHarness = await RouterTestingHarness.create();

    await routerTestingHarness.navigateByUrl(
      '/clients/C.1222/approvals/A.1234/users/testuser',
    );

    expect(approvalRequestStoreMock.fetchClientApproval).toHaveBeenCalledWith(
      'A.1234',
      'C.1222',
      'testuser',
    );
  }));
});
