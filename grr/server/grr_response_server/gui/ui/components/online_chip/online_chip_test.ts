import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {Component} from '@angular/core';
import {OnlineChipModule} from './module';
import {OnlineChip} from './online_chip';


// TestHostComponent is needed in order to trigger change detection in the
// underlying status observable. Creating a standalone status-chip
// instance doesn't trigger the ngOnChanges lifecycle hook:
// https://stackoverflow.com/questions/37408801/testing-ngonchanges-lifecycle-hook-in-angular-2
@Component({
  template: `<online-chip [lastSeen]="lastSeen"></online-chip>`
})
class TestHostComponent {
  lastSeen?: Date;
}

initTestEnvironment();

describe('Status Chip Component', () => {
  const STATUS_ONLINE = 'Online';
  const STATUS_OFFLINE = 'Offline';

  beforeEach(async(() => {
    TestBed
      .configureTestingModule({
        imports: [
          OnlineChipModule,
          NoopAnimationsModule,  // This makes test faster and more stable.
        ],
        declarations: [OnlineChip, TestHostComponent]
      })
      .compileComponents();
  }));

  beforeEach(() => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000')) // July 1, 2020, 13:00:00
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('shows "Online" for users last seen up to 15 minutes ago', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    fixture.detectChanges();

    componentInstance.lastSeen = new Date('2020-07-01T12:59:45');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_ONLINE);

    componentInstance.lastSeen = new Date('2020-07-01T12:50:45');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_ONLINE);

    componentInstance.lastSeen = new Date('2020-07-01T12:45:00.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_ONLINE);

    componentInstance.lastSeen = new Date('2020-07-01T12:45:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual(STATUS_ONLINE);
  });

  it('shows "Offline" for users last seen more than 15 minutes ago', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    fixture.detectChanges();

    componentInstance.lastSeen = new Date('2020-07-01T12:45:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_OFFLINE);

    componentInstance.lastSeen = new Date('2020-07-01T12:40:15');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_OFFLINE);

    componentInstance.lastSeen = new Date('1623-07-01T12:59:00.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_OFFLINE);
  });

  it('updates the status from "Online" to "Offline" as time passes by', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    fixture.detectChanges();

    componentInstance.lastSeen = new Date('2020-07-01T12:45:01.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_ONLINE);

    jasmine.clock().tick(1000);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_OFFLINE);
  });

  it('updates the status from "Offline" to "Online" when lastSeen updates', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const componentInstance = fixture.componentInstance;
    fixture.detectChanges();

    componentInstance.lastSeen = new Date('2020-07-01T12:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_OFFLINE);

    componentInstance.lastSeen = new Date('2020-07-01T13:00:00');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(STATUS_ONLINE);
  });
});
