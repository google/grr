import {Component, ContentChild, EventEmitter, Input, Output} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {initTestEnvironment} from '../../../testing';

import {TitleEditorModule} from './module';
import {TitleEditorContent} from './title_editor';

initTestEnvironment();

@Component({
  template:
      `<title-editor [disabled]="disabled" (changed)="changed.emit($event)">
               <h1 titleEditable>hello world</h1>
             </title-editor>`
})
class TestHostComponent {
  @Input() disabled = false;
  @Output() readonly changed = new EventEmitter<string>();
  @ContentChild(TitleEditorContent) content!: TitleEditorContent;
}

@Component({
  template: `<title-editor route="['foo']">
                    <h1 titleEditable>hello world with link</h1>
                  </title-editor>`
})
class TestHostComponentWithLink {
}

describe('params form test', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            TitleEditorModule,
            RouterTestingModule,
          ],
          declarations: [
            TestHostComponent,
            TestHostComponentWithLink,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('renders link', () => {
    const fixture = TestBed.createComponent(TestHostComponentWithLink);
    fixture.detectChanges();
    const icons = fixture.debugElement.queryAll(By.css('mat-icon'));
    expect(icons.length).toBe(3);
    const iconLink = fixture.debugElement.query(By.css('a'));
    expect(iconLink).toBeTruthy();
    expect(iconLink.attributes['href']).toContain('foo');
  });

  it('does not render link', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    const icons = fixture.debugElement.queryAll(By.css('mat-icon'));
    expect(icons.length).toBe(3);
    const iconLink = fixture.debugElement.query(By.css('a'));
    expect(iconLink).toBeFalsy();
  });

  it('renders the content as if editor is disabled', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('hello world');
    const buttonEl = fixture.debugElement.query(By.css('button')).nativeElement;
    expect(getComputedStyle(buttonEl).visibility).toEqual('hidden');
  });

  it('hides the edit button during edit and focuses the value',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(TestHostComponent);
       const editatbleEl =
           fixture.debugElement.query(By.css('h1')).nativeElement;
       spyOn(editatbleEl, 'focus');
       fixture.detectChanges();

       const button = fixture.debugElement.query(By.css('button'));
       button.triggerEventHandler('click', new MouseEvent('click'));
       tick(500);
       fixture.detectChanges();

       fixture.whenStable().then(() => {
         expect(fixture.debugElement.query(By.css('button'))).toBeNull();
         expect(editatbleEl.focus).toHaveBeenCalled();
       });
     }));

  it('saves the content on blur', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('button'));
    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    const editatbleEl = fixture.debugElement.query(By.css('h1')).nativeElement;
    expect(editatbleEl.textContent).toBe('hello world');

    editatbleEl.textContent = 'new value';
    editatbleEl.dispatchEvent(new Event('blur'));
    fixture.detectChanges();

    expect(editatbleEl.textContent).toBe('new value');
    expect(fixture.debugElement.query(By.css('.editing'))).toBeNull();
  });

  it('starts editing on focus', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('.editing'))).toBeNull();

    fixture.debugElement.query(By.css('.wrapper'))
        .nativeElement.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('.editing'))).not.toBeNull();
  });

  it('keeps the content stay unchanged on escape key', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('button'));
    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    const editatbleEl = fixture.debugElement.query(By.css('h1')).nativeElement;
    expect(editatbleEl.textContent).toBe('hello world');

    editatbleEl.textContent = 'new value';
    const event = new KeyboardEvent('keydown', {'key': 'ESCAPE'});
    editatbleEl.dispatchEvent(event);
    fixture.detectChanges();

    expect(editatbleEl.textContent).toBe('hello world');
    expect(fixture.debugElement.query(By.css('.editing'))).toBeNull();
  });
});
