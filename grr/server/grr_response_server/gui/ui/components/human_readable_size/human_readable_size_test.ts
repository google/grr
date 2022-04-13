import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';

import {HumanReadableSizeComponent} from './human_readable_size';
import {HumanReadableSizeModule} from './module';


initTestEnvironment();

describe('HumanReadableSizeComponent', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HumanReadableSizeModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('is blank when no size provided', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('');
  });

  it('is blank when the provided size is smaller than 0', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    fixture.componentInstance.size = -1024;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('');
  });

  it('shows the provided size in a human readable format', () => {
    const fixture = TestBed.createComponent(HumanReadableSizeComponent);
    const component = fixture.componentInstance;

    component.size = 0;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('0 B');

    component.size = 1 / 3;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('0 B');

    component.size = 1023;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023 B');

    component.size = 1023.9;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023 B');

    component.size = 1024;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 KiB');

    component.size = 1034;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 KiB');

    component.size = 1035;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.01 KiB');

    component.size = Math.pow(1024, 2) - 1;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023.99 KiB');

    component.size = Math.pow(1024, 2);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 MiB');

    component.size = Math.pow(1024, 3) - 1;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023.99 MiB');

    component.size = Math.pow(1024, 3);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 GiB');

    component.size = Math.pow(1024, 4) - 1;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023.99 GiB');

    component.size = Math.pow(1024, 4);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 TiB');

    component.size = Math.pow(1024, 5) - 1;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1023.99 TiB');

    component.size = Math.pow(1024, 5);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('1.00 PiB');

    component.size = Math.pow(1024, 6) * 324;
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toEqual('331776.00 PiB');
  });
});
