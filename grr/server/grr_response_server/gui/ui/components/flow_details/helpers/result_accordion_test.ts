import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {HelpersModule} from './module';




initTestEnvironment();


@Component({
  template: `
<result-accordion
    [title]="title"
    [hasMoreResults]="hasMoreResults"
    (loadMore)="loadMoreTriggered()">
    contenttext
</result-accordion>`
})
class TestHostComponent {
  title?: string;
  hasMoreResults: boolean = true;
  loadMoreTriggered = jasmine.createSpy('loadMoreTriggered');
}

describe('ResultAccordion Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: []
        })
        .compileComponents();
  }));

  function createComponent(args: Partial<TestHostComponent> = {}):
      ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.title = args.title;
    fixture.componentInstance.hasMoreResults = args.hasMoreResults ?? true;
    fixture.detectChanges();

    return fixture;
  }

  it('shows title', () => {
    const fixture = createComponent({title: 'foobar'});
    expect(fixture.debugElement.nativeElement.textContent).toContain('foobar');
  });

  it('shows content on click', () => {
    const fixture = createComponent({hasMoreResults: true});

    expect(fixture.debugElement.nativeElement.textContent)
        .not.toContain('contenttext');
    fixture.debugElement.query(By.css('.header')).nativeElement.click();
    fixture.detectChanges();
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('contenttext');
  });

  it('emits loadMore on first open', () => {
    const fixture = createComponent({hasMoreResults: true});
    expect(fixture.componentInstance.loadMoreTriggered).not.toHaveBeenCalled();

    fixture.debugElement.query(By.css('.header')).nativeElement.click();
    expect(fixture.componentInstance.loadMoreTriggered).toHaveBeenCalled();
  });
});
