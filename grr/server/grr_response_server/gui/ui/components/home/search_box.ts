import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {ApiSearchClientResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateClient} from '@app/lib/api_translation/client';
import {Client} from '@app/lib/models/client';
import {BehaviorSubject, fromEvent, Observable, of, Subject} from 'rxjs';
import {debounceTime, distinctUntilChanged, filter, map, switchMap, takeUntil, withLatestFrom} from 'rxjs/operators';

/**
 * Search box component.
 *
 * NOTE: This has no effective dependency on NgRx store. i.e. it's
 * self-contained, depends solely on its own input and not on a global state.
 */
@Component({
  selector: 'search-box',
  templateUrl: './search_box.ng.html',
  styleUrls: ['./search_box.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchBox implements AfterViewInit, OnDestroy {
  constructor(private readonly httpApiService: HttpApiService) {}

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

  private readonly unsubscribe$ = new Subject<void>();

  readonly clients$ = new BehaviorSubject<Client[]>([]);

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
                map(([, query]) => query),
                filter(query => query !== ''),
            );
    enterPressed$.pipe(takeUntil(this.unsubscribe$)).subscribe(query => {
      this.querySubmitted.emit(query);
    });

    this.inputFormControl.valueChanges
        .pipe(
            takeUntil(this.unsubscribe$),
            debounceTime(300),
            distinctUntilChanged(),
            switchMap(query => this.searchClients(query)),
            )
        .subscribe(this.clients$);
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  private searchClients(query: string) {
    let searchResults: Observable<ApiSearchClientResult>;
    if (query) {
      searchResults =
          this.httpApiService.searchClients({query, offset: 0, count: 100});
    } else {
      searchResults = of({items: []});
    }

    return searchResults.pipe(map(
        response => response.items ? response.items.map(translateClient) : []));
  }

  selectClient(clientId: string) {
    this.querySubmitted.emit(clientId);
  }

  trackClient(index: number, client: Client) {
    return client.clientId;
  }
}
