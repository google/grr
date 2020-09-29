import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {Subject} from 'rxjs';

import {newClientApproval} from '../../lib/models/model_test_util';
import {ApprovalPageFacade} from '../../store/approval_page_facade';
import {ApprovalPageFacadeMock, mockApprovalPageFacade} from '../../store/approval_page_facade_test_util';
import {ConfigFacade} from '../../store/config_facade';
import {mockConfigFacade} from '../../store/config_facade_test_util';
import {UserFacade} from '../../store/user_facade';
import {mockUserFacade} from '../../store/user_facade_test_util';
import {initTestEnvironment} from '../../testing';

import {ApprovalPage} from './approval_page';
import {ApprovalPageModule} from './approval_page_module';



initTestEnvironment();


describe('ApprovalPage Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let approvalPageFacade: ApprovalPageFacadeMock;

  // TODO(user): Change to waitForAsync once we run on Angular 10, which
  //  in turn requires TypeScript 3.9.
  // tslint:disable-next-line:deprecation
  beforeEach(async(() => {
    paramsSubject = new Subject();
    approvalPageFacade = mockApprovalPageFacade();

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
              provide: ApprovalPageFacade,
              useFactory: () => approvalPageFacade,
            },
            {
              provide: UserFacade,
              useFactory: mockUserFacade,
            },
            {
              provide: ConfigFacade,
              useFactory: mockConfigFacade,
            }
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

    expect(approvalPageFacade.selectApproval)
        .toHaveBeenCalledWith(
            {clientId: 'cid', requestor: 'req', approvalId: 'aid'});
  });

  it('displays approval information on client change', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    approvalPageFacade.approvalSubject.next(newClientApproval({
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

    approvalPageFacade.approvalSubject.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      status: {type: 'pending', reason: 'Need 1 more approver'},
    }));
    fixture.detectChanges();

    expect(approvalPageFacade.grantApproval).not.toHaveBeenCalled();
    fixture.debugElement.query(By.css('mat-card-actions button'))
        .triggerEventHandler('click', undefined);
    expect(approvalPageFacade.grantApproval).toHaveBeenCalled();
  });
});
