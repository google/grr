import {CdkCopyToClipboard} from '@angular/cdk/clipboard';
import {OverlayModule} from '@angular/cdk/overlay';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {Approval} from '../../lib/models/user';
import {ApprovalCardLocalStore} from '../../store/approval_card_local_store';
import {
  ApprovalCardLocalStoreMock,
  mockApprovalCardLocalStore,
} from '../../store/approval_card_local_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {ApprovalCard} from './approval_card';
import {ApprovalCardModule} from './module';

initTestEnvironment();

const UI_CONFIG_DURATIONS = {
  defaultAccessDurationSeconds: String(28 * 24 * 60 * 60), // 28 days in seconds
  maxAccessDurationSeconds: String(100 * 24 * 60 * 60), // 100 days in seconds
};

const PREEXISTING_NOW = Date.prototype.getTime;
function fakeNow() {
  return 1000; // "Now" is 1 second (1000 millis) past epoch
}

describe('ApprovalCard Component', () => {
  let approvalCardLocalStore: ApprovalCardLocalStoreMock;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    approvalCardLocalStore = mockApprovalCardLocalStore();
    configGlobalStore = mockConfigGlobalStore();

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, RouterTestingModule, ApprovalCardModule],
      providers: [
        {
          provide: ConfigGlobalStore,
          useFactory: () => configGlobalStore,
        },
        OverlayModule,
      ],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(ApprovalCardLocalStore, {
        useFactory: () => approvalCardLocalStore,
      })
      .compileComponents();
    Date.prototype.getTime = fakeNow;
  }));

  afterEach(() => {
    Date.prototype.getTime = PREEXISTING_NOW;
  });

  function createComponent(
    latestApproval: Approval | null = null,
    urlTree: string[] = [],
    validateOnStart = false,
    showDuration = false,
    editableDuration = false,
  ): ComponentFixture<ApprovalCard> {
    const fixture = TestBed.createComponent(ApprovalCard);
    fixture.componentInstance.latestApproval = latestApproval;
    fixture.componentInstance.urlTree = urlTree;
    fixture.componentInstance.validateOnStart = validateOnStart;
    fixture.componentInstance.showDuration = showDuration;
    fixture.componentInstance.editableDuration = editableDuration;
    spyOn(fixture.componentInstance.approvalParams, 'emit');
    fixture.detectChanges();
    return fixture;
  }

  it('validates form reason', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    fixture.detectChanges();

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(
      fixture.componentInstance.approvalParams.emit,
    ).not.toHaveBeenCalled();
    expect(fixture.debugElement.nativeElement.textContent).toContain(
      'required',
    );
  });

  it('validateOnStart triggers error message when rendering', () => {
    const fixture = createComponent(null, [], true);

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent).toContain(
      'required',
    );
  });

  it('FALSE validateOnStart does not show error before touched', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent).not.toContain(
      'required',
    );
  });

  it('requests approval when form is submitted', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    fixture.detectChanges();

    fixture.componentInstance.formRequestedApprovers.add('rick');
    fixture.componentInstance.formRequestedApprovers.add('jerry');
    fixture.componentInstance.form.patchValue({reason: 'sample reason'});

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit).toHaveBeenCalledWith({
      approvers: ['rick', 'jerry'],
      reason: 'sample reason',
      cc: [],
    });
  });

  it('requests approval when form is submitted with a non-default duration', () => {
    const fixture = createComponent(null, [], false, true, true);

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    configGlobalStore.mockedObservables.uiConfig$.next(UI_CONFIG_DURATIONS);

    fixture.debugElement.nativeElement.querySelector('.changeDuration').click();

    fixture.detectChanges();

    fixture.componentInstance.formRequestedApprovers.add('rick');
    fixture.componentInstance.formRequestedApprovers.add('jerry');
    fixture.componentInstance.form.patchValue({
      reason: 'sample reason',
      duration: 30,
    });

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit).toHaveBeenCalledWith({
      approvers: ['rick', 'jerry'],
      reason: 'sample reason',
      cc: [],
      expirationTimeUs: '31000000', // 31 seconds since epoch in microseconds
    });
  });

  it('Submit does not emit approvalParams if duration is higher than max allowed', () => {
    const fixture = createComponent(null, [], false, true, true);

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    configGlobalStore.mockedObservables.uiConfig$.next(UI_CONFIG_DURATIONS);
    fixture.detectChanges();

    fixture.debugElement.nativeElement.querySelector('.changeDuration').click();

    fixture.componentInstance.formRequestedApprovers.add('rick');
    fixture.componentInstance.formRequestedApprovers.add('jerry');
    fixture.componentInstance.form.patchValue({
      reason: 'sample reason',
      duration: Number(UI_CONFIG_DURATIONS.maxAccessDurationSeconds) + 100,
    });
    fixture.detectChanges();

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(
      fixture.componentInstance.approvalParams.emit,
    ).not.toHaveBeenCalled();
  });

  it('duration does no appear if showDuration is false', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    configGlobalStore.mockedObservables.uiConfig$.next(UI_CONFIG_DURATIONS);
    fixture.detectChanges();

    expect(
      fixture.debugElement.nativeElement.querySelector('.duration'),
    ).toBeNull();
  });

  it('duration is not editable if editableDuration is false', () => {
    const fixture = createComponent(null, [], false, true, false);

    configGlobalStore.mockedObservables.approvalConfig$.next({});
    configGlobalStore.mockedObservables.uiConfig$.next(UI_CONFIG_DURATIONS);
    fixture.detectChanges();

    expect(
      fixture.debugElement.nativeElement.querySelector('.changeDuration'),
    ).toBeNull();
  });

  it('loads and displays optional cc address for approval', () => {
    const fixture = createComponent();
    fixture.detectChanges();

    configGlobalStore.mockedObservables.approvalConfig$.next({
      optionalCcEmail: 'foo@example.org',
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo@example.org');
  });

  it('sets reason for approval value in form based on url param', async () => {
    await TestBed.inject(Router).navigate([], {
      queryParams: {reason: 'foo/t/abcd'},
    });

    const fixture = createComponent();
    fixture.detectChanges();

    expect(fixture.componentInstance.form.value.reason).toEqual('foo/t/abcd');
  });

  it('uses optional cc address for approval by default', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({
      optionalCcEmail: 'foo@example.org',
    });
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue({
      approvers: 'rick',
      reason: 'sample reason',
    });

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit).toHaveBeenCalledWith(
      jasmine.objectContaining({cc: ['foo@example.org']}),
    );
  });

  it('does not use optional cc if checkbox is unchecked', () => {
    const fixture = createComponent();

    configGlobalStore.mockedObservables.approvalConfig$.next({
      optionalCcEmail: 'foo@example.org',
    });
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue({
      approvers: 'rick',
      reason: 'sample reason',
      ccEnabled: false,
    });

    fixture.debugElement
      .query(By.css('form'))
      .triggerEventHandler('submit', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalParams.emit).toHaveBeenCalledWith(
      jasmine.objectContaining({cc: []}),
    );
  });

  it('shows pre-existing approval', () => {
    const latestApproval: Approval = {
      approvalId: '1',
      requestor: 'testuser',
      status: {type: 'pending', reason: 'Need at least 1 more approver.'},
      approvers: [],
      reason: 'sample reason',
      requestedApprovers: ['foo'],
    };
    const fixture = createComponent(latestApproval);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('foo');
    expect(text).toContain('sample reason');
  });

  it('allows copying the approval url', () => {
    const urlTree = ['some', 'url'];
    const latestApproval: Approval = {
      approvalId: '',
      requestor: '',
      status: {type: 'pending', reason: ''},
      approvers: [],
      reason: '',
      requestedApprovers: [''],
    };
    const fixture = createComponent(latestApproval, urlTree);
    fixture.detectChanges();

    const directiveEl = fixture.debugElement.query(
      By.directive(CdkCopyToClipboard),
    );
    expect(directiveEl).not.toBeNull();

    const expected = /^https?:\/\/.+\/some\/url$/;
    const copyToClipboard = directiveEl.injector.get(CdkCopyToClipboard);
    expect(copyToClipboard.text).toMatch(expected);
  });

  it('displays initial autocomplete suggestions', () => {
    const fixture = createComponent();
    fixture.detectChanges();

    expect(approvalCardLocalStore.suggestApprovers).toHaveBeenCalledWith('');
    const approversInput = fixture.debugElement.query(
      By.css('mat-chip-grid input'),
    );
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    approvalCardLocalStore.mockedObservables.approverSuggestions$.next([
      'bar',
      'baz',
    ]);
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

    const approversInput = fixture.debugElement.query(
      By.css('mat-chip-grid input'),
    );
    fixture.componentInstance.controls.approvers.setValue('ba');
    approversInput.triggerEventHandler('focusin', null);
    fixture.detectChanges();

    expect(approvalCardLocalStore.suggestApprovers).toHaveBeenCalledWith('ba');
    approvalCardLocalStore.mockedObservables.approverSuggestions$.next([
      'bar',
      'baz',
    ]);
    fixture.detectChanges();

    const matOptions = document.querySelectorAll('mat-option');
    expect(matOptions.length).toBe(2);
    expect(matOptions[0].textContent).toContain('bar');
    expect(matOptions[1].textContent).toContain('baz');
  });

  it('shows contents on click when closed', () => {
    const fixture = createComponent();
    fixture.componentInstance.hideContent = true;
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeTrue();

    fixture.debugElement.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('toggles contents on click on toggle button', () => {
    const fixture = createComponent();
    fixture.componentInstance.hideContent = true;
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
    const fixture = createComponent();
    fixture.componentInstance.hideContent = true;
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
    const latestApproval: Approval = {
      approvalId: '1',
      requestor: 'testuser',
      status: {type: 'valid'},
      approvers: [],
      reason: 'sample reason http://example.com',
      requestedApprovers: ['foo'],
    };

    const fixture = createComponent(latestApproval);
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('app-text-with-links a'));
    expect(link.attributes['href']).toEqual('http://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('sample reason http://example.com');
  });
});
