import {HttpErrorResponse} from '@angular/common/http';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {RequestStatusType} from '../../lib/api/track_request';
import {newClientApproval} from '../../lib/models/model_test_util';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {UserGlobalStore} from '../../store/user_global_store';
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
          teardown: {destroyAfterEach: false}
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

  it('shows a progress spinner when the approval request is in flight', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
    }));
    fixture.detectChanges();


    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        {status: RequestStatusType.SENT});
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner')))
        .not.toBeNull();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''})
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();
  });

  it('disables the grant button when a grant request is in flight', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
    }));
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        {status: RequestStatusType.SENT});
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''})
    });
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBeFalsy();
  });

  it('disables the grant button if the current user approved already', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      approvers: ['somebodyelse'],
    }));
    injectMockStore(UserGlobalStore)
        .mockedObservables.currentUser$.next(
            {name: 'approver', canaryMode: false, huntApprovalRequired: false});
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      approvers: ['approver'],
    }));
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('disables the grant button if the current user is the requestor', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newClientApproval({
      clientId: 'C.1234',
      requestor: 'requestor',
      reason: 'foobazzle 42',
      approvers: ['somebodyelse'],
    }));
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'requestor',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('linkifies tokens starting with http:// in request reason', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    injectMockStore(ApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newClientApproval({
          reason: 'foobazzle 42 http://example.com',
        }));
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('app-text-with-links a'));
    expect(link.attributes['href']).toEqual('http://example.com');
    expect(link.nativeElement.textContent).toEqual('http://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foobazzle 42 http://example.com');
  });
});
