import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, OnDestroy, Output, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {MatAutocompleteTrigger} from '@angular/material/autocomplete';
import {combineLatest, Subject} from 'rxjs';
import {debounceTime, distinctUntilChanged, filter, map, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';

import {Client} from '../../lib/models/client';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientSearchLocalStore} from '../../store/client_search_local_store';
import {ConfigGlobalStore} from '../../store/config_global_store';


const LABEL_IDENTIFIER = 'label';

/**
 * Search box component.
 */
@Component({
  selector: 'app-search-box',
  templateUrl: './search_box.ng.html',
  styleUrls: ['./search_box.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ClientSearchLocalStore]
})
export class SearchBox implements AfterViewInit, OnDestroy {
  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly clientSearchLocalStore: ClientSearchLocalStore) {}

  protected readonly inputFormControl =
      new FormControl('', {nonNullable: true});

  protected readonly formSubmitted$ = new Subject<void>();

  @ViewChild('input') input!: ElementRef<HTMLInputElement>;

  @Input() value?: string;

  /**
   * An event that is triggered every time when a user presses Enter. Emits the
   * query that's typed into the input element.
   */
  @Output() querySubmitted = new EventEmitter<string>();

  @Input() autofocus: boolean = false;

  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.querySubmitted.complete();
  });

  protected readonly clients$ = this.clientSearchLocalStore.clients$;

  private readonly searchQuery$ = this.inputFormControl.valueChanges.pipe(
      takeUntil(this.ngOnDestroy.triggered$),
      startWith(''),
  );

  private readonly debouncedSearchQuery$ = this.searchQuery$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
  );

  private readonly formattedClientsLabels$ =
      this.configGlobalStore.clientsLabels$.pipe(
          map(labels => labels.map(label => `${LABEL_IDENTIFIER}:${label}`)));

  protected readonly labels$ =
      combineLatest([this.searchQuery$, this.formattedClientsLabels$])
          .pipe(
              map(([query, allLabels]) => this.filterLabels(query, allLabels)),
          );

  @ViewChild(MatAutocompleteTrigger) autocomplete!: MatAutocompleteTrigger;

  ngAfterViewInit() {
    this.inputFormControl.setValue(this.value ?? '');

    this.formSubmitted$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            withLatestFrom(this.searchQuery$),
            map(([, query]) => query),
            filter(query => query !== ''),
            )
        .subscribe(query => {
          this.querySubmitted.emit(query);
          this.autocomplete.closePanel();
        });

    this.debouncedSearchQuery$.subscribe(query => {
      this.clientSearchLocalStore.searchClients(query);
    });

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

  protected selectClient(clientId: string) {
    this.querySubmitted.emit(clientId);
    this.autocomplete.closePanel();
  }

  protected trackClient(index: number, client: Client) {
    return client.clientId;
  }
}
