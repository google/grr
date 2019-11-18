import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {fromEvent, Subject} from 'rxjs';
import {distinctUntilChanged, filter, map, takeUntil, withLatestFrom} from 'rxjs/operators';


/**
 * Search box component.
 *
 * NOTE: this is an example of component that is intended to have a complex
 * autocomplete behavior, but has no effective dependency on NgRx store. I.e.
 * it's self-contained, depends solely on its own input and not on a global
 * state.
 */
@Component({
  selector: 'search-box',
  templateUrl: './search_box.ng.html',
  styleUrls: ['./search_box.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchBox implements AfterViewInit, OnDestroy {
  /** A binding for a reactive forms input element. */
  inputFormControl = new FormControl('');

  /**
   * A reference to a child input element. Guaranteed not to be null: it's
   * bound by Angular on component's initialization.
   */
  @ViewChild('input', {static: false}) input!: ElementRef;

  /**
   * An event that is triggered every time when a user presses Enter. Emits the
   * query that's typed into the input element.
   */
  @Output() querySubmitted = new EventEmitter<string>();

  private readonly unsubscribe = new Subject<void>();

  ngAfterViewInit() {
    // We can't initialize enterPressed$ as a class attribute, since it
    // depends on the ViewChild("input") which gets initialized after the
    // component is constructed.
    const enterPressed$ =
        fromEvent<KeyboardEvent>(this.input.nativeElement, 'keyup')
            .pipe(
                filter(e => e.key === 'Enter'),
                distinctUntilChanged(),
                withLatestFrom(this.inputFormControl.valueChanges),
                map(([event, query]) => query),
                filter(query => query !== ''),
            );
    enterPressed$.pipe(takeUntil(this.unsubscribe)).subscribe(query => {
      this.querySubmitted.emit(query);
    });
  }

  ngOnDestroy() {
    this.unsubscribe.next();
    this.unsubscribe.complete();
  }
}
