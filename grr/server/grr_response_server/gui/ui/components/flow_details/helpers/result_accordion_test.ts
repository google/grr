import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';
import {Status} from './result_accordion';



initTestEnvironment();


@Component({
  template: `
<result-accordion
    [title]="title"
    [expandable]="expandable"
    [description]="description"
    [preview]="preview"
    [status]="status"
    (firstOpened)="firstOpenedTriggered()">
    contenttext
</result-accordion>`
})
class TestHostComponent {
  title?: string;
  description?: string;
  preview?: string;
  status?: Status;
  expandable: boolean = true;
  firstOpenedTriggered = jasmine.createSpy('firstOpenedTriggered');
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
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function createComponent(args: Partial<TestHostComponent> = {}):
      ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.title = args.title;
    fixture.componentInstance.description = args.description;
    fixture.componentInstance.preview = args.preview;
    fixture.componentInstance.status = args.status;
    fixture.componentInstance.expandable = args.expandable ?? true;
    fixture.detectChanges();

    return fixture;
  }

  it('shows title', () => {
    const fixture = createComponent({title: 'foobar'});
    expect(fixture.debugElement.nativeElement.textContent).toContain('foobar');
  });

  it('shows content on click', () => {
    const fixture = createComponent({expandable: true});

    expect(fixture.debugElement.nativeElement.textContent)
        .not.toContain('contenttext');
    fixture.debugElement.query(By.css('.header')).nativeElement.click();
    fixture.detectChanges();
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('contenttext');
  });

  it('emits firstOpened on first open', () => {
    const fixture = createComponent({expandable: true});
    expect(fixture.componentInstance.firstOpenedTriggered)
        .not.toHaveBeenCalled();

    fixture.debugElement.query(By.css('.header')).nativeElement.click();
    expect(fixture.componentInstance.firstOpenedTriggered).toHaveBeenCalled();
  });

  it('shows description', () => {
    const fixture = createComponent({description: 'foobar-description'});
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('foobar-description');
  });

  it('shows preview', () => {
    const fixture = createComponent({preview: 'foobar-preview'});
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('foobar-preview');
  });

  it('shows status icon and styling', () => {
    const fixture = createComponent({status: Status.WARNING});
    const iconEl = fixture.debugElement.query(By.css('.warning .mat-icon'));
    expect(iconEl.nativeElement.textContent).toContain('warning');
  });
});
