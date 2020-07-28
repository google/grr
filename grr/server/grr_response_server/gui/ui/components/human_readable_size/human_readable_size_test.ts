import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '../../testing';
import {HumanReadableSizeModule} from './module';
import {HumanReadableSizeComponent} from './human_readable_size';

initTestEnvironment();

describe('HumanReadableSizeComponent', () => {

  beforeEach(async(() => {
    TestBed
      .configureTestingModule({
        imports: [
          NoopAnimationsModule,
          HumanReadableSizeModule,
        ],
      })
      .compileComponents();

  }));

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('shows "-" when no size provided', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('-');
  });

  it('shows "-" when the provided size is smaller than 0', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    fixture.componentInstance.size = -1024;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('-');
  });

  it('shows the provided size in a human readable format', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    const component = fixture.componentInstance;

    component.size = 0;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('0 B');

    component.size = 1023;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023 B');

    component.size = 1024;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.0 KiB');

    component.size = Math.pow(1024, 2);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.0 MiB');

    component.size = Math.pow(1024, 3);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.0 GiB');

    component.size = Math.pow(1024, 4);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.0 TiB');

    component.size = Math.pow(1024, 5);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.0 PiB');

    component.size = Math.pow(1024, 6) * 324;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('331776.0 PiB');
  });
});
