import {Component, ElementRef, input, ViewChild} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {FormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {SubmitOnMetaEnterDirective} from './submit_on_meta_enter_directive';

initTestEnvironment();

@Component({
  template: `
    <form #form (submit)="onSubmit($event)" [appSubmitOnMetaEnter]="appSubmitOnMetaEnter()" [appSubmitOnEnter]="appSubmitOnEnter()">
      <input #input id="input">
      <button type="button" #button (click)="onButtonClick($event)"></button>
      <input type="submit" #submit>
    </form>`,
  imports: [SubmitOnMetaEnterDirective, FormsModule],
})
class TestHostComponent {
  readonly appSubmitOnMetaEnter = input<boolean>(true);
  readonly appSubmitOnEnter = input<boolean>();

  readonly onSubmit = jasmine.createSpy('submit').and.callFake((event) => {
    event.preventDefault();
  });
  readonly onButtonClick = jasmine
    .createSpy('button:click')
    .and.callFake((event) => {
      event.preventDefault();
    });

  @ViewChild('form') form!: ElementRef<HTMLFormElement>;
  @ViewChild('input') input!: ElementRef<HTMLInputElement>;
  @ViewChild('button') button!: ElementRef<HTMLButtonElement>;
  @ViewChild('submit') submit!: ElementRef<HTMLInputElement>;
  @ViewChild(SubmitOnMetaEnterDirective) directive!: SubmitOnMetaEnterDirective;
}

describe('Submit On Meta Enter directive', () => {
  let fixture: ComponentFixture<TestHostComponent>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TestHostComponent],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
  }));

  it('submits on META+ENTER press', () => {
    expect(fixture.componentInstance.onSubmit).not.toHaveBeenCalled();
    fixture.componentInstance.form.nativeElement.dispatchEvent(
      new KeyboardEvent('keydown', {key: 'Enter', metaKey: true}),
    );
    fixture.detectChanges();
    expect(fixture.componentInstance.onSubmit).toHaveBeenCalledTimes(1);
  });

  it('submits on CTRL+ENTER press', () => {
    expect(fixture.componentInstance.onSubmit).not.toHaveBeenCalled();
    fixture.componentInstance.form.nativeElement.dispatchEvent(
      new KeyboardEvent('keydown', {key: 'Enter', ctrlKey: true}),
    );
    fixture.detectChanges();
    expect(fixture.componentInstance.onSubmit).toHaveBeenCalledTimes(1);
  });

  it('does not submit for ENTER presses on input field', () => {
    // Testing organic event bubbling and cancellation seems hard/impossible in
    // Angular unit tests. As a last resort, we pass the event directly to the
    // callback and check how the event is operated on.
    const event: Partial<KeyboardEvent> = {
      preventDefault: jasmine.createSpy('preventDefault'),
      stopPropagation: jasmine.createSpy('stopPropagation'),
      key: 'Enter',
      metaKey: false,
      ctrlKey: false,
      target: fixture.componentInstance.input.nativeElement,
    };

    fixture.componentInstance.directive.onKeyPress(event as KeyboardEvent);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(fixture.componentInstance.onSubmit).not.toHaveBeenCalled();
  });

  it('submits for ENTER if appSubmitOnEnter is set', () => {
    fixture.componentRef.setInput('appSubmitOnEnter', true);
    fixture.detectChanges();

    const event: Partial<KeyboardEvent> = {
      preventDefault: jasmine.createSpy('preventDefault'),
      stopPropagation: jasmine.createSpy('stopPropagation'),
      key: 'Enter',
      metaKey: false,
      ctrlKey: false,
      target: fixture.componentInstance.input.nativeElement,
    };

    fixture.componentInstance.directive.onKeyPress(event as KeyboardEvent);
    expect(fixture.componentInstance.onSubmit).toHaveBeenCalledTimes(1);
  });

  it('does not affect other key presses', () => {
    const event: Partial<KeyboardEvent> = {
      preventDefault: jasmine.createSpy('preventDefault'),
      stopPropagation: jasmine.createSpy('stopPropagation'),
      key: 'a',
      metaKey: true,
      ctrlKey: false,
      target: fixture.componentInstance.input.nativeElement,
    };

    fixture.componentInstance.directive.onKeyPress(event as KeyboardEvent);

    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(event.stopPropagation).not.toHaveBeenCalled();
    expect(fixture.componentInstance.onSubmit).not.toHaveBeenCalled();
  });

  it('does not affect ENTER on button element', () => {
    const event: Partial<KeyboardEvent> = {
      preventDefault: jasmine.createSpy('preventDefault'),
      stopPropagation: jasmine.createSpy('stopPropagation'),
      key: 'Enter',
      metaKey: false,
      ctrlKey: false,
      target: fixture.componentInstance.button.nativeElement,
    };

    fixture.componentInstance.directive.onKeyPress(event as KeyboardEvent);

    expect(event.preventDefault).not.toHaveBeenCalled();
    expect(event.stopPropagation).not.toHaveBeenCalled();
    expect(fixture.componentInstance.onSubmit).not.toHaveBeenCalled();
  });
});
