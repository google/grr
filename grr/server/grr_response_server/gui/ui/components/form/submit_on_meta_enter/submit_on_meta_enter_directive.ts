import {Directive, ElementRef, Input} from '@angular/core';

const shouldPassThroughEnter = (target: EventTarget|null) =>
    // If the focussed element is a button (likely by TAB-ing),  allow ENTER
    // to activate the active button.
    (target instanceof HTMLButtonElement) ||
    (target instanceof HTMLInputElement &&
         (target.type === 'submit' || target.type === 'button') ||
     // If the focussed element is a textarea, allow newlines by typing ENTER.
     (target instanceof HTMLTextAreaElement));

const isMetaPressed = (event: KeyboardEvent) => event.metaKey || event.ctrlKey;

const isEnterPressed = (event: KeyboardEvent) => event.key === 'Enter';

/**
 * Enables form submit on CMD/CTRL + ENTER press. Prevents accidental submit
 * when only pressing ENTER.
 */
@Directive({
  selector: 'form[appSubmitOnMetaEnter]',
  host: {
    '(keypress)': 'onKeyPress($event)',
    '(keydown)': 'onKeyDown($event)',
  },
})
export class SubmitOnMetaEnterDirective {
  /**
   * Enables form submit on CMD/CTRL + ENTER press. Unless [appSubmitOnEnter] is
   * set, prevents accidental submit when only pressing ENTER.
   */
  @Input() appSubmitOnMetaEnter?: boolean = true;

  /**
   * Re-allows submitting the form on ENTER, which is prevented by default in
   * [appSubmitOnMetaEnter].
   */
  @Input() appSubmitOnEnter?: boolean = false;

  constructor(private readonly elementRef: ElementRef<HTMLFormElement>) {}

  onKeyPress(event: KeyboardEvent) {
    if (!this.appSubmitOnMetaEnter) {
      return;  // Directive has been disabled.
    }

    if (!isEnterPressed(event)) {
      return;  // Pass through and ignore all non-ENTER presses.
    }

    if (shouldPassThroughEnter(event.target)) {
      return;
    }

    if (this.appSubmitOnEnter) {
      // When desiring ENTER to trigger submit, prevent default behavior and
      // trigger the submit.
      event.preventDefault();
      event.stopPropagation();
      this.elementRef.nativeElement.requestSubmit();
    } else {
      // Prevent ENTER presses from accidentally submitting the form. This
      // prevents a variety of accidents, e.g. the user presses ENTER once to
      // select an autocompletion entry and presses ENTER again which submits
      // the whole form.
      event.preventDefault();
    }
  }

  onKeyDown(event: KeyboardEvent) {
    if (!this.appSubmitOnMetaEnter) {
      return;  // Directive has been disabled.
    }

    if (isEnterPressed(event) && isMetaPressed(event)) {
      // If the user presses CMD/CTRL + ENTER, submit the form. For some reason,
      // CMD+ENTER is not triggering (keypress), which is why we catch this
      // event in keydown already.
      event.preventDefault();
      event.stopPropagation();
      this.elementRef.nativeElement.requestSubmit();
    }
  }
}
