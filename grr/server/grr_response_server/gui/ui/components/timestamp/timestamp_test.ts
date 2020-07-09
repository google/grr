import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {TimestampModule} from './module';
import {Timestamp} from './timestamp';
import {By} from '@angular/platform-browser';

initTestEnvironment();

describe('Timestamp Component', () => {

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

  it('shows "Unknown" when no date is provided', () => {
    const fixture = TestBed.createComponent(Timestamp);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('Unknown');
  });

  it('only shows short timestamp by default', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    const date = new Date('2020-07-01T12:59:59');
    componentInstance.date = date;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('2020-07-01 12:59:59 UTC');
  });

  it('shows long timestamp when completeFormat parameter is set to true', () => {
    const fixture = TestBed.createComponent(Timestamp);
    const componentInstance = fixture.componentInstance;

    const date = new Date('2020-07-01T12:50:00');
    componentInstance.date = date;
    componentInstance.completeFormat = true;
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('.timestamp')).nativeElement.innerText)
      .toEqual('2020-07-01 12:50:00 UTC 10 minutes ago content_copy');
  });
});
