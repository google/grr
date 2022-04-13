import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, OnDestroy, Output, ViewChild} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';
import {BehaviorSubject, fromEvent, Observable, of} from 'rxjs';
import {debounceTime, distinctUntilChanged, filter, map, switchMap, takeUntil, withLatestFrom} from 'rxjs/operators';

import {ApiSearchClientResult} from '../../lib/api/api_interfaces';
import {HttpApiService} from '../../lib/api/http_api_service';
import {translateClient} from '../../lib/api_translation/client';
import {Client} from '../../lib/models/client';
import {observeOnDestroy} from '../../lib/reactive';
import {ConfigGlobalStore} from '../../store/config_global_store';


const LABEL_IDENTIFIER = 'label';

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
  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly httpApiService: HttpApiService) {}

  /** A binding for a reactive forms input element. */
  readonly inputFormControl = new UntypedFormControl('');

  /**
   * A reference to a child input element. Guaranteed not to be null: it's
   * bound by Angular on component's initialization.
   */
  @ViewChild('input') input!: ElementRef<HTMLInputElement>;

  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  /**
   * An event that is triggered every time when a user presses Enter. Emits the
   * query that's typed into the input element.
   */
  @Output() querySubmitted = new EventEmitter<string>();

  @Input() autofocus: boolean = false;

  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.querySubmitted.complete();
  });

  private readonly formattedClientsLabels$ =
      this.configGlobalStore.clientsLabels$.pipe(
          map(labels => labels.map(label => `${LABEL_IDENTIFIER}:${label}`)));

  readonly clients$ = new BehaviorSubject<Client[]>([]);
  readonly labels$ = new BehaviorSubject<string[]>([]);

  ngAfterViewInit() {
    // We can't initialize fromEvent as a class attribute, since it
    // depends on the ViewChild("input") which gets initialized after the
    // component is constructed.
    fromEvent<SubmitEvent>(this.form.nativeElement, 'submit', {capture: true})
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            withLatestFrom(this.inputFormControl.valueChanges),
            map(([, query]) => query),
            filter(query => query !== ''),
            )
        .subscribe(query => {
          this.querySubmitted.emit(query);
        });

    const valueChanged$ = this.inputFormControl.valueChanges.pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        debounceTime(300),
        distinctUntilChanged(),
    );

    valueChanged$.pipe(switchMap((query: string) => this.searchClients(query)))
        .subscribe(this.clients$);

    valueChanged$
        .pipe(
            withLatestFrom(this.formattedClientsLabels$),
            map(([query, allLabels]) => this.filterLabels(query, allLabels)))
        .subscribe(this.labels$);

    if (this.autofocus) {
      this.input.nativeElement.focus();
    }
  }



  private filterLabels(query: string, allLabels: string[]) {
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 3) {
      return [];
    }

    return allLabels.filter(label => label.startsWith(trimmedQuery))
        .slice(0, 8);
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
