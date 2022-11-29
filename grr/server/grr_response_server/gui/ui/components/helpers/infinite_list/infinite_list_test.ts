
import {Component, Input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {InfiniteListModule} from './infinite_list_module';

initTestEnvironment();

@Component({
  template: `
    <app-infinite-list [hasMore]="hasMore" [isLoading]="isLoading" (loadMore)="loadMore()">
    </app-infinite-list>`
})
class TestHostComponent {
  @Input() hasMore: boolean|null = null;
  @Input() isLoading: boolean|null = null;
  readonly loadMore = jasmine.createSpy('loadMore');
}

const originalIntersectionObserver = window.IntersectionObserver;

describe('InfiniteList', () => {
  // tslint:disable:no-any
  let observe: ((entries: any, observer: any) => void) = () => {};

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            InfiniteListModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    // tslint:disable:no-any
    (window as any).IntersectionObserver = class MockIntersectionObserver {
      constructor(cb: IntersectionObserverCallback) {
        observe = cb;
      }
      observe = jasmine.createSpy('observe');
    };
  }));

  afterEach(() => {
    window.IntersectionObserver = originalIntersectionObserver;
    observe = () => {};
  });

  it('shows spinner when isLoading is true', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-spinner'))).toBeNull();

    fixture.componentInstance.isLoading = true;
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-spinner'))).not.toBeNull();
  });

  it('shows load more button when hasMore is true', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button'))).toBeNull();

    fixture.componentInstance.hasMore = true;
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button'))).not.toBeNull();
  });

  it('hides load more button when isLoading is true', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.hasMore = true;
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button'))).not.toBeNull();

    fixture.componentInstance.isLoading = true;
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button'))).toBeNull();
  });

  it('triggers loadMore when hasMore is true and footer enters view',
     async () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.componentInstance.hasMore = true;
       fixture.detectChanges();

       expect(fixture.componentInstance.loadMore).not.toHaveBeenCalled();

       observe([{isIntersecting: true}], null);
       fixture.detectChanges();

       expect(fixture.componentInstance.loadMore).toHaveBeenCalledOnceWith();
     });

  it('triggers loadMore when footer is in view and hasMore changes to true',
     async () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.componentInstance.hasMore = false;
       fixture.detectChanges();
       observe([{isIntersecting: true}], null);
       fixture.detectChanges();

       expect(fixture.componentInstance.loadMore).not.toHaveBeenCalled();

       fixture.componentInstance.hasMore = true;
       fixture.detectChanges();

       expect(fixture.componentInstance.loadMore).toHaveBeenCalledOnceWith();
     });

  it('triggers loadMore when loadMore button is clicked', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.hasMore = true;
    fixture.detectChanges();

    expect(fixture.componentInstance.loadMore).not.toHaveBeenCalled();

    fixture.debugElement.query(By.css('button'))
        .triggerEventHandler('click', null);
    fixture.detectChanges();

    expect(fixture.componentInstance.loadMore).toHaveBeenCalledOnceWith();
  });
});
