import {Component, Input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {Duration} from '../../../lib/date_time';
import {HuntState} from '../../../lib/models/hunt';
import {newHunt} from '../../../lib/models/model_test_util';

import {HuntStatusChip} from './hunt_status_chip';
import {HuntStatusChipModule} from './module';


@Component({
  template: `<app-hunt-status-chip [hunt]="hunt"></app-hunt-status-chip>`,
})
class TestHostComponent {
  @Input() hunt: HuntStatusChip['hunt'] = null;
}

describe('HuntStatusChip', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntStatusChipModule,
          ],
          declarations: [
            TestHostComponent,
          ],
        })
        .compileComponents();
  }));

  it('shows "Collection paused" for "Started" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.PAUSED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection paused');
  });

  it('shows "Collection stopped" for "Stopped" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.STOPPED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection stopped');
  });

  it('shows "Collection completed" for "Completed" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.COMPLETED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection completed');
  });

  it('shows "Collection running" for "Started" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.STARTED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection running');
  });

  it('shows "left" for "Started" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    // 3 days plus buffer to unflake the test.
    const threeDays = Duration.fromObject({day: 3, minute: 1});
    fixture.componentInstance.hunt =
        newHunt({state: HuntState.STARTED, duration: threeDays});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('3 days left');
  });
});
