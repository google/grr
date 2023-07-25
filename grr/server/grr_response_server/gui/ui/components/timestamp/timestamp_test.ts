import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Subject} from 'rxjs';

import {initTestEnvironment} from '../../testing';

import {TimestampModule} from './module';
import {Timestamp, TimestampRefreshTimer} from './timestamp';

initTestEnvironment();

describe('Timestamp Component', () => {
  let timer$ = new Subject<void>();

  beforeEach(waitForAsync(() => {
    timer$ = new Subject<void>();

    TestBed
        .configureTestingModule({
          imports: [
            TimestampModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          providers: [
            {
              // Emulating the actual RxJS timer is very finicky, for unclear
              // reasons jasmine.clock().install() breaks unrelated tests and
              // Angular's tick() and jasmine.clock().tick() interfere.
              // Ultimately, we mock the whole Timer for a clean, controllable
              // alternative.
              provide: TimestampRefreshTimer,
              useFactory: (): TimestampRefreshTimer => ({timer$}),
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('is blank when no date is provided', () => {
    const fixture = TestBed.createComponent(Timestamp);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('');
  });

  it('only shows short timestamp by default', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T12:59:59+00:00');
       fixture.detectChanges();
       expect(fixture.nativeElement.innerText)
           .toContain('2020-07-01 12:59:59 UTC');
     }));

  it('shows the relative timestamp when relativeTimestamp is set to visible',
     fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T12:50:00+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText)
           .toContain('2020-07-01 12:50:00 UTC');
       expect(fixture.nativeElement.innerText).toContain('10 minutes ago');
     }));

  it('shows the relative timestamp when relativeTimestamp is set to tooltip',
     fakeAsync(async () => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T12:50:00+00:00');
       componentInstance.relativeTimestamp = 'tooltip';
       fixture.detectChanges();

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const harness = await harnessLoader.getHarness(MatTooltipHarness);
       await harness.show();
       expect(await harness.getTooltipText()).toEqual('10 minutes ago');
     }));


  it('renders "less than 1 minute ago" for a diff of 59 seconds',
     fakeAsync(() => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:00:59.000+00:00'));

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText)
           .toContain('less than 1 minute ago');
     }));

  it('renders "less than 1 minute ago" for a diff of 0', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();


       expect(fixture.nativeElement.innerText)
           .toContain('less than 1 minute ago');
     }));

  it('renders 1 minute ago for a diff of 60 seconds', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:01:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('1 minute ago');
     }));

  it('renders 59 minutes ago for a diff of 59 minutes', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:59:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('59 minutes ago');
     }));

  it('renders 1 hour ago for a diff of 60 minutes', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T14:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('1 hour ago');
     }));

  it('changes value when input date is changed', fakeAsync(() => {
       jasmine.clock().mockDate(new Date(
           '2020-07-01T13:00:00.000+00:00'));  // July 1, 2020, 13:00:00

       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T12:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('1 hour ago');

       componentInstance.date = new Date('2020-07-01T11:00:00.000+00:00');
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('2 hours ago');
     }));


  it('changes relative timestamp when time passes', fakeAsync(() => {
       jasmine.clock().mockDate(new Date('2020-07-01T13:01:00.000+00:00'));
       const fixture = TestBed.createComponent(Timestamp);
       const componentInstance = fixture.componentInstance;

       componentInstance.date = new Date('2020-07-01T13:00:00.000+00:00');
       componentInstance.relativeTimestamp = 'visible';
       fixture.detectChanges();

       jasmine.clock().mockDate(new Date('2020-07-01T13:01:59.000+00:00'));
       timer$.next();
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('1 minute ago');

       jasmine.clock().mockDate(new Date('2020-07-01T13:02:00.000+00:00'));
       timer$.next();
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('2 minutes ago');
     }));
});
