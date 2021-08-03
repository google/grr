import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';

import {newClientApproval} from '../../lib/models/model_test_util';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';

import {ApprovalPage} from './approval_page';
import {ApprovalPageModule} from './approval_page_module';

import {APPROVAL_ROUTES} from './routing';


initTestEnvironment();


describe('ApprovalPage Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            RouterTestingModule.withRoutes(APPROVAL_ROUTES),
            ApiModule,
            NoopAnimationsModule,
            ApprovalPageModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],

        })
        .compileComponents();

    TestBed.inject(Router).navigate(['clients/cid/users/req/approvals/aid']);
  }));

  it('should be created', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('loads approval information on route change', async () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    expect(injectMockStore(ApprovalPageGlobalStore).selectApproval)
        .toHaveBeenCalledWith(
            {clientId: 'cid', requestor: 'req', approvalId: 'aid'});
  });

  it('displays approval information on client change', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    injectMockStore(ApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newClientApproval({
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

    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);

    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
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
