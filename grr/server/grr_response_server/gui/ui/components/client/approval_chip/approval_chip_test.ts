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
});
