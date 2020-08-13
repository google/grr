import {CdkCopyToClipboard} from '@angular/cdk/clipboard';
import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {Client, ClientApproval} from '../../lib/models/client';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';

import {Approval} from './approval';


initTestEnvironment();

function makeClient(args: Partial<Client> = {}): Client {
  return {
    clientId: 'C.1234',
    fleetspeakEnabled: true,
    knowledgeBase: {},
    labels: [],
    ...args,
  };
}

describe('Approval Component', () => {
  let selectedClient$: Subject<Client>;
  let latestApproval$: Subject<ClientApproval>;
  let clientPageFacade: Partial<ClientPageFacade>;
  let configFacade: ConfigFacadeMock;

  beforeEach(async(() => {
    selectedClient$ = new Subject();
    latestApproval$ = new Subject();
    clientPageFacade = {
      selectedClient$,
      latestApproval$,
      requestApproval: jasmine.createSpy('requestApproval'),
    };
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
          ],

          providers: [
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
            {provide: ConfigFacade, useFactory: () => configFacade}
          ]
        })
        .compileComponents();
  }));

  it('requests approval when form is submitted', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());
    configFacade.approvalConfigSubject.next({});

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick,jerry', reason: 'sample reason'});

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

    selectedClient$.next(makeClient());

    configFacade.approvalConfigSubject.next(
        {optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo@example.org');
  });

  it('uses optional cc address for approval by default', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());

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

    selectedClient$.next(makeClient());

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

    selectedClient$.next(makeClient());
    latestApproval$.next({
      approvalId: '1',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo');
    expect(text).toContain('sample reason');
  });

  it('allows copying the approval url', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());
    latestApproval$.next({
      approvalId: '111',
      clientId: 'C.1234',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
    });
    fixture.detectChanges();

    const directiveEl =
        fixture.debugElement.query(By.directive(CdkCopyToClipboard));
    expect(directiveEl).not.toBeNull();

    const expected =
        /^https?:\/\/.+#\/users\/testuser\/approvals\/client\/C\.1234\/111$/;
    const copyToClipboard = directiveEl.injector.get(CdkCopyToClipboard);
    expect(copyToClipboard.text).toMatch(expected);
  });
});
