import {FormControl} from '@angular/forms';

/** Creates an array containing a form control for each word on the list. */
export function toStringFormControls(words: string[]):
    Array<FormControl<string>> {
  return words.map(word => new FormControl(word, {nonNullable: true}));
}