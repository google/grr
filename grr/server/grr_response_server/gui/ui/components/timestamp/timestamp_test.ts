import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {TimestampModule} from './module';
import {Timestamp} from './timestamp';
import {DatePipe} from '@angular/common';

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

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('shows "Just now" for dates less than 30s ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    componentInstance.date = new Date();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText).toEqual('Just now');
  });

  it('shows "Xmin ago" for dates less than one hour ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date();
    date.setMinutes(date.getMinutes() - 3);

    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText).toEqual('3min ago');
  });

  it('shows "XhYmin ago" for dates less than 24 hours ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date();
    date.setMinutes(date.getMinutes() - 3);
    date.setHours(date.getHours() - 3);
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText).toEqual('3h3min ago');
  });


  it('shows "yesterday at HH:mm" for dates less than 48 hours ago', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date();
    date.setMinutes(date.getMinutes() - 3);
    date.setHours(date.getHours() - 24);

    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText)
      .toEqual('yesterday at ' + new DatePipe('en').transform(date, 'HH:mm'));
  });

  it('shows absolute timstamp for dates older than 48 hours', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date();
    date.setMinutes(date.getMinutes() - 3);
    date.setHours(date.getHours() - 48);

    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText)
      .toEqual(new DatePipe('en').transform(date, ABSOLUTE_FORMAT));
  });

  it('shows absolute timestamp when absoluteOnly parameter is set', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    let date = new Date();
    date.setMinutes(date.getMinutes() - 3);

    componentInstance.date = date;
    componentInstance.absoluteOnly = true;
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('div').innerText)
      .toEqual(new DatePipe('en').transform(date, ABSOLUTE_FORMAT));
  });
});
