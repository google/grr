import {HttpErrorResponse} from '@angular/common/http';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router, RouterModule} from '@angular/router';

import {ApiModule} from '../../lib/api/module';
import {RequestStatusType} from '../../lib/api/track_request';
import {newClientApproval} from '../../lib/models/model_test_util';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {
  injectMockStore,
  STORE_PROVIDERS,
} from '../../store/store_test_providers';
import {UserGlobalStore} from '../../store/user_global_store';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';
import {APPROVAL_PAGE_ROUTES} from '../app/routing';

import {ApprovalPage} from './approval_page';
import {ApprovalPageModule} from './approval_page_module';

initTestEnvironment();

describe('ApprovalPage Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [
        ApiModule,
        NoopAnimationsModule,
        ApprovalPageModule,
        RouterModule.forRoot(APPROVAL_PAGE_ROUTES),
      ],
      providers: [
        ...STORE_PROVIDERS,
        {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    TestBed.inject(Router).navigate(['clients/cid/users/req/approvals/aid']);
  }));

  it('should be created', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('loads approval information on route change', async () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    expect(
      injectMockStore(ApprovalPageGlobalStore).selectApproval,
    ).toHaveBeenCalledWith({
      clientId: 'cid',
      requestor: 'req',
      approvalId: 'aid',
    });
  });

  it('displays approval information on client change', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    const twentyEightDaysFromNow = new Date(
      // 28 days minus 1 hour in ms.
      Date.now() + 28 * 24 * 60 * 60 * 1000 - 1000 * 60 * 60,
    );

    injectMockStore(ApprovalPageGlobalStore).mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        expirationTime: twentyEightDaysFromNow,
      }),
    );
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('msan');
    expect(text).toContain('foobazzle 42');
    expect(text).toContain('in 27 days'); // Rounds down

    const timestampCell = fixture.nativeElement.querySelector(
      'app-timestamp span.ts_component_timestamp span.contents',
    );
    expect(timestampCell).not.toBeNull();

    // The date is within the default expiration - should be no warning highlight
    const timestampChip = fixture.nativeElement.querySelector(
      'mat-chip.yellow-chip',
    );
    expect(timestampChip).toBeNull();
  });

  it('displays a correct expiration date string', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    const twentyEightDaysFromEpoch = new Date(28 * 24 * 60 * 60 * 1000 - 1000);

    injectMockStore(ApprovalPageGlobalStore).mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        expirationTime: twentyEightDaysFromEpoch,
      }),
    );
    fixture.detectChanges();

    const timestampCell = fixture.nativeElement.querySelector(
      'app-timestamp span.ts_component_timestamp span.contents',
    );
    expect(timestampCell).not.toBeNull();
    expect(timestampCell.textContent).toEqual('1970-01-28 23:59:59 UTC');
  });

  it('lengthy expiration on an approval request is highlighted', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    const fourHundredDaysFromNow = new Date(
      Date.now() + 400 * 24 * 60 * 60 * 1000 - 1000,
    );

    injectMockStore(ApprovalPageGlobalStore).mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        expirationTime: fourHundredDaysFromNow,
      }),
    );
    injectMockStore(ConfigGlobalStore).mockedObservables.uiConfig$.next({
      defaultAccessDurationSeconds: String(28 * 24 * 60 * 60), // 28 days in seconds
    });
    fixture.detectChanges();

    const timestampChip = fixture.nativeElement.querySelector(
      'mat-chip.yellow-chip',
    );
    expect(timestampChip).not.toBeNull();
    expect(timestampChip.textContent).toEqual(
      'warning This duration is longer than the default of 28 days. ',
    );
  });

  it('grants approval on button click', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    fixture.detectChanges();

    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);

    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    fixture.detectChanges();

    expect(approvalPageGlobalStore.grantApproval).not.toHaveBeenCalled();
    fixture.debugElement
      .query(By.css('mat-card-actions button'))
      .triggerEventHandler('click', undefined);
    expect(approvalPageGlobalStore.grantApproval).toHaveBeenCalled();
  });

  it('shows a progress spinner when the approval request is in flight', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
      }),
    );
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.SENT,
    });
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('button mat-spinner')),
    ).not.toBeNull();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''}),
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();
  });

  it('disables the grant button when a grant request is in flight', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
      }),
    );
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
      undefined,
    );
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.SENT,
    });
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');

    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''}),
    });
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBeFalsy();
  });

  it('disables the grant button if the current user approved already', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        approvers: ['somebodyelse'],
      }),
    );
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
      undefined,
    );
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'msan',
        reason: 'foobazzle 42',
        approvers: ['approver'],
      }),
    );
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('disables the grant button if the current user is the requestor', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    const approvalPageGlobalStore = injectMockStore(ApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'requestor',
        reason: 'foobazzle 42',
        approvers: ['somebodyelse'],
      }),
    );
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'requestor',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
      undefined,
    );
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('linkifies tokens starting with http:// in request reason', () => {
    const fixture = TestBed.createComponent(ApprovalPage);
    injectMockStore(ApprovalPageGlobalStore).mockedObservables.approval$.next(
      newClientApproval({
        reason: 'foobazzle 42 http://example.com',
      }),
    );
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('app-text-with-links a'));
    expect(link.attributes['href']).toEqual('http://example.com');
    expect(link.nativeElement.textContent).toEqual('http://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foobazzle 42 http://example.com');
  });
});
