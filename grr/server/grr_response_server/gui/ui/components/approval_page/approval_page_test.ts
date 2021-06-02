import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {Subject} from 'rxjs';

import {newClientApproval} from '../../lib/models/model_test_util';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {ApprovalPageGlobalStoreMock, mockApprovalPageGlobalStore} from '../../store/approval_page_global_store_test_util';
import {ClientDetailsGlobalStore} from '../../store/client_details_global_store';
import {mockClientDetailsGlobalStore} from '../../store/client_details_global_store_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {mockScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store_test_util';
import {UserGlobalStore} from '../../store/user_global_store';
import {mockUserGlobalStore} from '../../store/user_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {ApprovalPage} from './approval_page';
import {ApprovalPageModule} from './approval_page_module';



initTestEnvironment();


describe('ApprovalPage Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let approvalPageGlobalStore: ApprovalPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    paramsSubject = new Subject();
    approvalPageGlobalStore = mockApprovalPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            RouterTestingModule.withRoutes([]),
            ApiModule,
            NoopAnimationsModule,
            ApprovalPageModule,
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
              },
            },
            {
              provide: ApprovalPageGlobalStore,
              useFactory: () => approvalPageGlobalStore,
            },
            {
              provide: UserGlobalStore,
              useFactory: mockUserGlobalStore,
            },
            {
              provide: ConfigGlobalStore,
              useFactory: mockConfigGlobalStore,
            },
            {
              provide: ClientDetailsGlobalStore,
              useFactory: mockClientDetailsGlobalStore,
            },
            {
              provide: ClientPageGlobalStore,
              useFactory: mockClientPageGlobalStore,
            },
            {
              provide: ScheduledFlowGlobalStore,
              useFactory: mockScheduledFlowGlobalStore,
            },
          ],

        })
        .compileComponents();
  }));

  it('should be created', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('loads approval information on route change', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    paramsSubject.next(new Map(Object.entries(
        {clientId: 'cid', requestor: 'req', approvalId: 'aid'})));
    fixture.detectChanges();

    expect(approvalPageGlobalStore.selectApproval)
        .toHaveBeenCalledWith(
            {clientId: 'cid', requestor: 'req', approvalId: 'aid'});
  });

  it('displays approval information on client change', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    approvalPageGlobalStore.approvalSubject.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
    }));
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('msan');
    expect(text).toContain('foobazzle 42');
  });

  it('grants approval on button click', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    approvalPageGlobalStore.approvalSubject.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      status: {type: 'pending', reason: 'Need 1 more approver'},
    }));
    fixture.detectChanges();

    expect(approvalPageGlobalStore.grantApproval).not.toHaveBeenCalled();
    fixture.debugElement.query(By.css('mat-card-actions button'))
        .triggerEventHandler('click', undefined);
    expect(approvalPageGlobalStore.grantApproval).toHaveBeenCalled();
  });
});
