import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {TimestampModule} from './module';
import {Timestamp} from './timestamp';
import {DatePipe} from '@angular/common';
import {notDeepEqual} from 'assert';
import {DateTime} from 'luxon';

initTestEnvironment();

describe('Timestamp Component', () => {
  const ABSOLUTE_FORMAT: string = "MMM d \''yy 'at' HH:mm";

  beforeEach(async(() => {
    TestBed
      .configureTestingModule({
        imports: [
          TimestampModule,
          NoopAnimationsModule,  // This makes test faster and more stable.
        ],
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
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('shows "Just now" for dates less than 1min ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    const JUST_NOW = 'Just now';

    componentInstance.date = new Date('2020-07-01T12:59:59');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(JUST_NOW);

    componentInstance.date = new Date('2020-07-01T12:59:45');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(JUST_NOW);

    componentInstance.date = new Date('2020-07-01T12:59:30.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual(JUST_NOW);

    componentInstance.date = new Date('2020-07-01T12:59:30.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual(JUST_NOW);
  });

  it('shows "X seconds ago" for dates between 30s and 1min ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    const JUST_NOW = 'Just now';

    componentInstance.date = new Date('2020-07-01T12:59:30.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('30 seconds ago');

    componentInstance.date = new Date('2020-07-01T12:59:15');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('45 seconds ago');

    componentInstance.date = new Date('2020-07-01T12:59:00.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('59 seconds ago');

    componentInstance.date = new Date('2020-07-01T12:59:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual('59 seconds ago');
    expect(fixture.nativeElement.innerText).not.toEqual('60 seconds ago');
  });

  it('shows "Xmin ago" for dates between 1 minute and 1 hour ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    componentInstance.date = new Date('2020-07-01T12:59:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1min ago');

    componentInstance.date = new Date('2020-07-01T12:29:30.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('30min ago');

    componentInstance.date = new Date('2020-07-01T12:00:01.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('59min ago');

    componentInstance.date = new Date('2020-07-01T12:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual('59min ago');
    expect(fixture.nativeElement.innerText).not.toEqual('60min ago');
  });

  it('shows "XhYmin ago" for dates between 1 hour than 24 hours ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    componentInstance.date = new Date('2020-07-01T12:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1h0min ago');

    componentInstance.date = new Date('2020-07-01T01:25:00');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('11h35min ago');

    componentInstance.date = new Date('2020-06-30T13:00:00.001');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('23h59min ago');

    componentInstance.date = new Date('2020-06-30T13:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual('23h59min ago');
    expect(fixture.nativeElement.innerText).not.toEqual('24h0min ago');
  });


  it('shows "yesterday at HH:mm" for dates between 24 hours ago and yesterday beginning of day', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    componentInstance.date = new Date('2020-06-30T13:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('yesterday at 13:00');

    componentInstance.date = new Date('2020-06-30T08:23:23.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('yesterday at 08:23');

    componentInstance.date = new Date('2020-06-30T00:01:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual('yesterday at 00:01');

    componentInstance.date = new Date('2020-06-30T00:00:00.000');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toEqual('yesterday at 00:00');
  });

  it('shows absolute timestamp for dates older than yesterday beginning of day', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date('2020-06-29T23:59:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));

    date = new Date('1620-06-20T12:59:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));
  });

  it('shows absolute timestamp when absoluteOnly parameter is set', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    componentInstance.absoluteOnly = true;

    // Just now
    let date = new Date('2020-07-01T12:59:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));

    // 50 seconds ago
    date = new Date('2020-07-01T12:59:09.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));

    // 10min ago
    date = new Date('2020-07-01T12:50:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));

    // 9h10min ago
    date = new Date('2020-07-01T03:50:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));

    // yesterday at 03:50
    date = new Date('2020-06-30T03:50:59.999');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText)
      .toEqual(DateTime.fromJSDate(date).toLocaleString(DateTime.DATETIME_MED));
  });
});
