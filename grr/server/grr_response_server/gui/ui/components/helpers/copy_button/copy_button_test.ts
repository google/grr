import {Clipboard} from '@angular/cdk/clipboard';
import {Component, Input} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {CopyButtonModule} from './copy_button_module';

@Component({
  template:
      '<app-copy-button [overrideCopyText]="overrideCopyText">{{ text }}</app-copy-button>'
})
class TestComponentWithTextNode {
  @Input() text: string = '';
  @Input() overrideCopyText: string|undefined|null = undefined;
}

@Component({
  template:
      '<app-copy-button><div class="test-el">{{ text }}</div></app-copy-button>'
})
class TestComponentWithElementNode {
  @Input() text: string = '';
}

describe('CopyButton component', () => {
  let clipboard: Partial<Clipboard>;

  beforeEach((() => {
    clipboard = {
      copy: jasmine.createSpy('copy').and.returnValue(true),
    };

    TestBed
        .configureTestingModule({
          imports: [
            MatSnackBarModule, CopyButtonModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          declarations:
              [TestComponentWithTextNode, TestComponentWithElementNode],
          providers: [

            {
              provide: Clipboard,
              useFactory: () => clipboard,
            },
          ]
        })
        .compileComponents();
  }));

  it('should render text contents', () => {
    const fixture = TestBed.createComponent(TestComponentWithTextNode);
    fixture.componentInstance.text = 'test content';
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('test content');
    expect(fixture.debugElement.query(By.css('div.test-el'))).toBeNull();
  });

  it('should render element contents', () => {
    const fixture = TestBed.createComponent(TestComponentWithElementNode);
    fixture.componentInstance.text = 'test content';
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('test content');
    expect(fixture.debugElement.query(By.css('div.test-el'))).toBeTruthy();
  });

  it('shows a copy confirmation when clicking on copy', () => {
    const fixture = TestBed.createComponent(TestComponentWithTextNode);
    fixture.componentInstance.text = 'test content';
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain('check');
    expect(fixture.nativeElement.textContent).toContain('content_copy');

    fixture.debugElement.query(By.css('app-copy-button'))
        .triggerEventHandler('click', new MouseEvent('click'));

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain('content_copy');
    expect(fixture.nativeElement.textContent).toContain('check');
  });

  it('copies the text content to the clipboard on click', () => {
    const fixture = TestBed.createComponent(TestComponentWithTextNode);
    fixture.componentInstance.text = 'test content';
    fixture.detectChanges();

    expect(clipboard.copy).not.toHaveBeenCalled();

    fixture.debugElement.query(By.css('app-copy-button'))
        .triggerEventHandler('click', new MouseEvent('click'));

    expect(clipboard.copy).toHaveBeenCalledOnceWith('test content');
  });

  it('copies overrideCopyText if provided', () => {
    const fixture = TestBed.createComponent(TestComponentWithTextNode);
    fixture.componentInstance.text = 'test content';
    fixture.componentInstance.overrideCopyText = 'overridden content';
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent)
        .not.toContain('overridden content');
    expect(fixture.nativeElement.textContent).toContain('test content');

    fixture.debugElement.query(By.css('app-copy-button'))
        .triggerEventHandler('click', new MouseEvent('click'));

    expect(clipboard.copy).toHaveBeenCalledOnceWith('overridden content');
  });
});
