import {Component, Input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newClientApproval} from '../../../lib/models/model_test_util';

import {ApprovalChip} from './approval_chip';
import {ApprovalChipModule} from './approval_chip_module';


@Component({
  template: `<app-approval-chip [approval]="approval"></app-approval-chip>`,
})
class TestHostComponent {
  @Input() approval: ApprovalChip['approval'] = null;
}

describe('ApprovalChip', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ApprovalChipModule,
          ],
          declarations: [
            TestHostComponent,
          ],
        })
        .compileComponents();
  }));

  it('shows "No access" for missing approval', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval =
        newClientApproval({status: {type: 'invalid', reason: ''}});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('No access');
  });

  it('shows "Access granted" for valid approval', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval =
        newClientApproval({status: {type: 'valid'}});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Access granted');
  });

  it('shows "left" for valid approval', () => {
    const threeDaysMs = 1000 * 60 * 60 * 24 * 3;
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval = newClientApproval({
      status: {type: 'valid'},
      expirationTime: new Date(Date.now() + threeDaysMs)
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('left');
  });

  it('does not show "left" for invalid approval', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval =
        newClientApproval({status: {type: 'invalid', reason: ''}});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('left');
  });

  it('shows 3 days and one hour left as "3 days left"', () => {
    const threeDaysMs = 1000 * 60 * 60 * 24 * 3;
    const oneHourOneMinMs = 1000 * 60 * 61;  // 1min buffer
    const mockExpirationTimeMs = Date.now() + threeDaysMs + oneHourOneMinMs;

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval = newClientApproval({
      status: {type: 'valid'},
      expirationTime: new Date(mockExpirationTimeMs)
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('3 days left');
  });

  it('shows 61 minutes left as "1 hour left"', () => {
    const sixtyOneMinutesMs = 1000 * 60 * 61;
    const mockExpirationTimeMs = Date.now() + sixtyOneMinutesMs;

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.approval = newClientApproval({
      status: {type: 'valid'},
      expirationTime: new Date(mockExpirationTimeMs)
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('1 hour left');
  });
});
