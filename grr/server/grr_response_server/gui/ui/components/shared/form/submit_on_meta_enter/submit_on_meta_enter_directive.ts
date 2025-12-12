import {Directive, ElementRef, inject, input} from '@angular/core';

function shouldPassThroughEnter(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLButtonElement ||
    (target instanceof HTMLInputElement &&
      (target.type === 'submit' || target.type === 'button')) ||
    // If the focussed element is a textarea, allow newlines by typing ENTER.
    target instanceof HTMLTextAreaElement
  );
}

function isMetaPressed(event: KeyboardEvent): boolean {
  return event.metaKey || event.ctrlKey;
}

function isEnterPressed(event: KeyboardEvent): boolean {
  return event.key === 'Enter';
}

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
  private readonly elementRef = inject(ElementRef<HTMLFormElement>);

  /**
   * Enables form submit on CMD/CTRL + ENTER press. Unless [appSubmitOnEnter] is
   * set, prevents accidental submit when only pressing ENTER.
   */
  readonly appSubmitOnMetaEnter = input.required<boolean>();

  /**
   * Re-allows submitting the form on ENTER, which is prevented by default in
   * [appSubmitOnMetaEnter].
   */
  readonly appSubmitOnEnter = input<boolean>();

  onKeyPress(event: KeyboardEvent): void {
    if (!this.appSubmitOnMetaEnter()) {
      return; // Directive has been disabled.
    }

    if (!isEnterPressed(event)) {
      return; // Pass through and ignore all non-ENTER presses.
    }

    if (shouldPassThroughEnter(event.target)) {
      return;
    }

    if (this.appSubmitOnEnter()) {
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

  onKeyDown(event: KeyboardEvent): void {
    if (!this.appSubmitOnMetaEnter()) {
      return; // Directive has been disabled.
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
