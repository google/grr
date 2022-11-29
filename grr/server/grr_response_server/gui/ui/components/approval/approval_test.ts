import {CdkCopyToClipboard} from '@angular/cdk/clipboard';
import {OverlayModule} from '@angular/cdk/overlay';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ClientApproval} from '../../lib/models/client';
import {newClient} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {Approval} from './approval';
import {ApprovalModule} from './module';

initTestEnvironment();

describe('Approval Component', () => {
  let clientPageGlobalStore: ClientPageGlobalStoreMock;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    clientPageGlobalStore = mockClientPageGlobalStore();
    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RouterTestingModule,
            ApprovalModule,
          ],
          providers: [
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore
            },
            {
              provide: ConfigGlobalStore,
              useFactory: () => configGlobalStore,
            },
            OverlayModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));


  function createComponent(latestApproval: ClientApproval|null = null):
      ComponentFixture<Approval> {
    const fixture = TestBed.createComponent(Approval);
    fixture.componentInstance.latestApproval = latestApproval;
    spyOn(fixture.componentInstance.approvalParams, 'emit');
    fixture.detectChanges();
    return fixture;
  }

  it('requests approval when form is submitted', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    fixture.detectChanges();

    fixture.componentInstance.formRequestedApprovers.add('rick');
    fixture.componentInstance.formRequestedApprovers.add('jerry');
    fixture.componentInstance.form.patchValue({reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit).toHaveBeenCalledWith({
      approvers: ['rick', 'jerry'],
      reason: 'sample reason',
      cc: [],
    });
  });

  it('loads and displays optional cc address for approval', () => {
    const fixture = createComponent();
    fixture.detectChanges();

    configGlobalStore.mockedObservables.approvalConfig$.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo@example.org');
  });

  it('sets reason for approval value in form based on url param', async () => {
    await TestBed.inject(Router).navigate(
        [], {queryParams: {reason: 'foo/t/abcd'}});

    const fixture = createComponent();
    fixture.detectChanges();

    expect(fixture.componentInstance.form.value.reason).toEqual('foo/t/abcd');
  });

  it('uses optional cc address for approval by default', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit)
        .toHaveBeenCalledWith(
            jasmine.objectContaining({cc: ['foo@example.org']}));
  });

  it('does not use optional cc if checkbox is unchecked', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason', ccEnabled: false});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit)
        .toHaveBeenCalledWith(jasmine.objectContaining({cc: []}));
  });

  it('shows pre-existing approval', () => {
    const client = newClient({
      clientId: 'C.1234',
      ...{},
    });
    const latestApproval: ClientApproval = {
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: client,
    };
    const fixture = createComponent(latestApproval);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo');
    expect(text).toContain('sample reason');
  });

  it('allows copying the approval url', () => {
    const client = newClient({
      clientId: 'C.1234',
      ...{},
    });
    const latestApproval: ClientApproval = {
      approvalId: '111',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: client,
    };
    const fixture = createComponent(latestApproval);
    fixture.detectChanges();

    const directiveEl =
        fixture.debugElement.query(By.directive(CdkCopyToClipboard));
    expect(directiveEl).not.toBeNull();

    const expected =
        /^https?:\/\/.+\/clients\/C.1234\/users\/testuser\/approvals\/111$/;
    const copyToClipboard = directiveEl.injector.get(CdkCopyToClipboard);
    expect(copyToClipboard.text).toMatch(expected);
  });

  it('displays initial autocomplete suggestions', () => {
    const fixture = createComponent();
    fixture.detectChanges();
    configGlobalStore.mockedObservables.approvalConfig$.next({});

    expect(clientPageGlobalStore.suggestApprovers).toHaveBeenCalledWith('');

    const approversInput =
        fixture.debugElement.query(By.css('mat-chip-list input'));
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.approverSuggestions$.next(
        ['bar', 'baz']);
    fixture.detectChanges();

    const matOptions = document.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('bar');
    expect(matOptions[1].textContent).toContain('baz');
  });

  it('displays autocomplete suggestions when typing', () => {
    const fixture = createComponent();
    fixture.detectChanges();

    configGlobalStore.mockedObservables.approvalConfig$.next({});

    const approversInput =
        fixture.debugElement.query(By.css('mat-chip-list input'));
    fixture.componentInstance.approversInputControl.setValue('ba');
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    expect(clientPageGlobalStore.suggestApprovers).toHaveBeenCalledWith('ba');
    clientPageGlobalStore.mockedObservables.approverSuggestions$.next(
        ['bar', 'baz']);
    fixture.detectChanges();

    const matOptions = document.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('bar');
    expect(matOptions[1].textContent).toContain('baz');
  });

  it('shows contents on click when closed', () => {
    const latestApproval: ClientApproval = {
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'valid'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: newClient({clientId: 'C.1234'}),
    };
    const fixture = createComponent(latestApproval);

    expect(fixture.componentInstance.hideContent).toBeTrue();

    fixture.debugElement.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('toggles contents on click on toggle button', () => {
    const latestApproval: ClientApproval = {
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'valid'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: newClient({clientId: 'C.1234'}),
    };
    const fixture = createComponent(latestApproval);
    const button = fixture.debugElement.query(By.css('#approval-card-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();
  });

  it('opens contents on click on header', () => {
    const latestApproval: ClientApproval = {
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'valid'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: newClient({clientId: 'C.1234'}),
    };
    const fixture = createComponent(latestApproval);
    const header = fixture.debugElement.query(By.css('.header'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    header.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();

    // Do not toggle when clicking on header again, but stay open.
    header.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('linkifies tokens starting with http:// in request reason', () => {
    const latestApproval: ClientApproval = {
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'valid'},
      approvers: [],
      reason: 'sample reason http://example.com',
      requestedApprovers: ['foo'],
      subject: newClient({clientId: 'C.1234'}),
    };

    const fixture = createComponent(latestApproval);
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('app-text-with-links a'));
    expect(link.attributes['href']).toEqual('http://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('sample reason http://example.com');
  });
});
