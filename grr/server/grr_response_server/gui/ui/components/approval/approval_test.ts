import {CdkCopyToClipboard} from '@angular/cdk/clipboard';
import {OverlayModule} from '@angular/cdk/overlay';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {initTestEnvironment} from '@app/testing';
import {of} from 'rxjs';

import {Client} from '../../lib/models/client';
import {newClient} from '../../lib/models/model_test_util';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ClientPageFacadeMock, mockClientPageFacade} from '../../store/client_page_facade_test_util';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';

import {Approval} from './approval';
import {ApprovalModule} from './module';


initTestEnvironment();

function makeClient(args: Partial<Client> = {}): Client {
  return newClient({
    clientId: 'C.1234',
    ...args,
  });
}

describe('Approval Component', () => {
  let clientPageFacade: ClientPageFacadeMock;
  let configFacade: ConfigFacadeMock;

  beforeEach(waitForAsync(() => {
    clientPageFacade = mockClientPageFacade();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RouterTestingModule.withRoutes([]),
            ApprovalModule,
          ],

          providers: [
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
            {provide: ConfigFacade, useFactory: () => configFacade},
            OverlayModule,
            {
              provide: ActivatedRoute,
              useFactory: () => {
                const route = new ActivatedRoute();
                route.queryParams = of({reason: 'vimes/t/abcd'});
                return route;
              }
            },
          ]
        })
        .compileComponents();
  }));

  it('requests approval when form is submitted', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());
    configFacade.approvalConfigSubject.next({});

    fixture.componentInstance.formRequestedApprovers.add('rick');
    fixture.componentInstance.formRequestedApprovers.add('jerry');
    fixture.componentInstance.form.patchValue({reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientPageFacade.requestApproval).toHaveBeenCalledWith({
      clientId: 'C.1234',
      approvers: ['rick', 'jerry'],
      reason: 'sample reason',
      cc: [],
    });
  });

  it('loads and displays optional cc address for approval', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());

    configFacade.approvalConfigSubject.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo@example.org');
  });

  it('sets reason for approval value in form based on url param', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    expect(fixture.componentInstance.form.value.reason).toEqual('vimes/t/abcd');
  });

  it('uses optional cc address for approval by default', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());

    configFacade.approvalConfigSubject.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientPageFacade.requestApproval)
        .toHaveBeenCalledWith(
            jasmine.objectContaining({cc: ['foo@example.org']}));
  });

  it('does not use optional cc if checkbox is unchecked', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());

    configFacade.approvalConfigSubject.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason', ccEnabled: false});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientPageFacade.requestApproval)
        .toHaveBeenCalledWith(jasmine.objectContaining({cc: []}));
  });

  it('shows pre-existing approval', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    const client = makeClient();
    clientPageFacade.selectedClientSubject.next(client);
    clientPageFacade.latestApprovalSubject.next({
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: client,
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo');
    expect(text).toContain('sample reason');
  });

  it('allows copying the approval url', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    const client = makeClient();
    clientPageFacade.selectedClientSubject.next(client);
    clientPageFacade.latestApprovalSubject.next({
      approvalId: '111',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
      subject: client,
    });
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
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());
    configFacade.approvalConfigSubject.next({});

    expect(clientPageFacade.suggestApprovers).toHaveBeenCalledWith('');

    const approversInput =
        fixture.debugElement.query(By.css('mat-chip-list input'));
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    clientPageFacade.approverSuggestionsSubject.next(['bar', 'baz']);
    fixture.detectChanges();

    const matOptions = document.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('bar');
    expect(matOptions[1].textContent).toContain('baz');
  });

  it('displays autocomplete suggestions when typing', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(makeClient());
    configFacade.approvalConfigSubject.next({});

    const approversInput =
        fixture.debugElement.query(By.css('mat-chip-list input'));
    fixture.componentInstance.approversInputControl.setValue('ba');
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    expect(clientPageFacade.suggestApprovers).toHaveBeenCalledWith('ba');
    clientPageFacade.approverSuggestionsSubject.next(['bar', 'baz']);
    fixture.detectChanges();

    const matOptions = document.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('bar');
    expect(matOptions[1].textContent).toContain('baz');
  });

  it('shows contents on click when closed', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    fixture.debugElement.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(Approval);
    const button = fixture.debugElement.query(By.css('h1 button'));
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
    const fixture = TestBed.createComponent(Approval);
    const header = fixture.debugElement.query(By.css('h1'));
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
});
