import {Component, OnDestroy} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {firstValueFrom, lastValueFrom} from 'rxjs';

import {initTestEnvironment} from '../testing';

import {observeOnDestroy} from './reactive';

initTestEnvironment();

@Component({template: ''})
class TestComponent implements OnDestroy {
  readonly callback = jasmine.createSpy('callback');
  readonly ngOnDestroy = observeOnDestroy(this, this.callback);
}

describe('observeOnDestroy', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          declarations: [TestComponent],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('emits triggered$ when called', async () => {
    const fixture = TestBed.createComponent(TestComponent);
    const promise =
        firstValueFrom(fixture.componentInstance.ngOnDestroy.triggered$);
    fixture.destroy();
    expect(await promise).toBeUndefined();
  });

  it('completes triggered$ when called', async () => {
    const fixture = TestBed.createComponent(TestComponent);
    const promise =
        lastValueFrom(fixture.componentInstance.ngOnDestroy.triggered$);
    fixture.destroy();
    expect(await promise).toBeUndefined();
  });

  it('invokes callback when called', async () => {
    const fixture = TestBed.createComponent(TestComponent);
    const callback = fixture.componentInstance.callback;

    fixture.detectChanges();
    expect(callback).not.toHaveBeenCalled();
    fixture.destroy();
    expect(callback).toHaveBeenCalledOnceWith();
  });

  it('prototype assignment does not interfere with other instances',
     async () => {
       const fixture1 = TestBed.createComponent(TestComponent);
       const callback1 = fixture1.componentInstance.callback;

       const fixture2 = TestBed.createComponent(TestComponent);
       const callback2 = fixture2.componentInstance.callback;

       const fixture3 = TestBed.createComponent(TestComponent);
       const callback3 = fixture3.componentInstance.callback;

       expect(callback1).not.toHaveBeenCalled();
       expect(callback2).not.toHaveBeenCalled();
       expect(callback3).not.toHaveBeenCalled();

       fixture2.destroy();

       expect(callback1).not.toHaveBeenCalled();
       expect(callback2).toHaveBeenCalledOnceWith();
       expect(callback3).not.toHaveBeenCalled();
     });
});
