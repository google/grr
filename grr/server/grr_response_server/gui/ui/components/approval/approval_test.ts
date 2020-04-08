import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {ApprovalConfig, Client, ClientApproval} from '../../lib/models/client';
import {ClientFacade} from '../../store/client_facade';

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
  let approvalConfig$: Subject<ApprovalConfig>;
  let latestApproval$: Subject<ClientApproval>;
  let clientFacade: Partial<ClientFacade>;

  beforeEach(async(() => {
    selectedClient$ = new Subject();
    approvalConfig$ = new Subject();
    latestApproval$ = new Subject();
    clientFacade = {
      selectedClient$,
      approvalConfig$,
      latestApproval$,
      requestApproval: jasmine.createSpy('requestApproval'),
      fetchApprovalConfig: jasmine.createSpy('fetchApprovalConfig'),
      listClientApprovals: jasmine.createSpy('listClientApprovals'),
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
          ],

          providers: [{provide: ClientFacade, useValue: clientFacade}]
        })
        .compileComponents();
  }));

  it('requests approval when form is submitted', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());
    approvalConfig$.next({});

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick,jerry', reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientFacade.requestApproval).toHaveBeenCalledWith({
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

    expect(clientFacade.fetchApprovalConfig).toHaveBeenCalled();

    approvalConfig$.next({optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo@example.org');
  });

  it('uses optional cc address for approval by default', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());

    approvalConfig$.next({optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason'});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientFacade.requestApproval)
        .toHaveBeenCalledWith(
            jasmine.objectContaining({cc: ['foo@example.org']}));
  });

  it('does not use optional cc if checkbox is unchecked', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());

    approvalConfig$.next({optionalCcEmail: 'foo@example.org'});
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue(
        {approvers: 'rick', reason: 'sample reason', ccEnabled: false});

    fixture.debugElement.query(By.css('form'))
        .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(clientFacade.requestApproval)
        .toHaveBeenCalledWith(jasmine.objectContaining({cc: []}));
  });

  it('shows pre-existing approval', () => {
    const fixture = TestBed.createComponent(Approval);
    fixture.detectChanges();

    selectedClient$.next(makeClient());
    latestApproval$.next({
      approvalId: '1',
      clientId: 'C.1234',
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
});
