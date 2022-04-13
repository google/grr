import {Component} from '@angular/core';
import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';

import {OnlineChipModule} from './module';
import {OnlineChip} from './online_chip';

// TestHostComponent is needed in order to trigger change detection in the
// underlying status observable. Creating a standalone status-chip
// instance doesn't trigger the ngOnChanges lifecycle hook:
// https://stackoverflow.com/questions/37408801/testing-ngonchanges-lifecycle-hook-in-angular-2
@Component({template: `<online-chip [lastSeen]="lastSeen"></online-chip>`})
class TestHostComponent {
  lastSeen?: Date;
}

initTestEnvironment();

describe('Status Chip Component', () => {
  const STATUS_ONLINE = 'Online';
  const STATUS_OFFLINE = 'Offline';

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            OnlineChipModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          declarations: [OnlineChip, TestHostComponent],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('shows "Online" for clients last seen up to 15 minutes ago',
     fakeAsync(() => {
       jasmine.clock().mockDate(
           new Date('2020-07-01T13:00:00.000'));  // July 1, 2020, 13:00:00
       const fixture = TestBed.createComponent(TestHostComponent);
       const componentInstance = fixture.componentInstance;
       fixture.detectChanges();

       componentInstance.lastSeen = new Date('2020-07-01T12:59:45');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_ONLINE);

       componentInstance.lastSeen = new Date('2020-07-01T12:50:45');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_ONLINE);

       componentInstance.lastSeen = new Date('2020-07-01T12:45:00.001');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_ONLINE);

       componentInstance.lastSeen = new Date('2020-07-01T12:45:00.000');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).not.toContain(STATUS_ONLINE);

       discardPeriodicTasks();
     }));

  it('shows "Offline" for clients last seen more than 15 minutes ago',
     fakeAsync(() => {
       jasmine.clock().mockDate(
           new Date('2020-07-01T13:00:00.000'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(TestHostComponent);
       const componentInstance = fixture.componentInstance;
       fixture.detectChanges();

       componentInstance.lastSeen = new Date('2020-07-01T12:45:00.000');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_OFFLINE);

       componentInstance.lastSeen = new Date('2020-07-01T12:40:15');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_OFFLINE);

       componentInstance.lastSeen = new Date('1623-07-01T12:59:00.001');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_OFFLINE);

       discardPeriodicTasks();
     }));

  it('updates the status from "Online" to "Offline" when time crosses the threshold',
     fakeAsync(() => {
       jasmine.clock().mockDate(
           new Date('2020-07-01T13:00:00.000'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(TestHostComponent);
       const componentInstance = fixture.componentInstance;
       fixture.detectChanges();

       componentInstance.lastSeen = new Date('2020-07-01T12:45:01.000');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_ONLINE);

       jasmine.clock().mockDate(
           new Date('2020-07-01T13:00:01.000'));  // July 1, 2020, 13:00:00
       tick(1000);
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_OFFLINE);
       discardPeriodicTasks();
     }));

  it('updates the status from "Offline" to "Online" when lastSeen updates',
     fakeAsync(() => {
       jasmine.clock().mockDate(
           new Date('2020-07-01T13:00:00.000'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(TestHostComponent);
       const componentInstance = fixture.componentInstance;
       fixture.detectChanges();

       componentInstance.lastSeen = new Date('2020-07-01T12:00:00.000');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_OFFLINE);

       componentInstance.lastSeen = new Date('2020-07-01T13:00:00');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText).toContain(STATUS_ONLINE);

       discardPeriodicTasks();
     }));
});
