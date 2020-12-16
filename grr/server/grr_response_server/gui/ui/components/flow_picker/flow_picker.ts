import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {MatAutocompleteTrigger} from '@angular/material/autocomplete';
import {FuzzyMatcher, StringWithHighlights, stringWithHighlightsFromMatch} from '@app/lib/fuzzy_matcher';
import {isNonNull} from '@app/lib/preconditions';
import {BehaviorSubject, fromEvent, merge, Observable, Subject} from 'rxjs';
import {debounceTime, filter, map, mapTo, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';

import {FlowListItem, FlowListItemService, FlowsByCategory} from './flow_list_item';



interface FlowAutoCompleteOption {
  readonly title: StringWithHighlights;
  readonly flowListItem: FlowListItem;
}

interface FlowAutoCompleteCategory {
  readonly title: StringWithHighlights;
  readonly options: ReadonlyArray<FlowAutoCompleteOption>;
}

function stringWithHighlightsFromString(s: string): StringWithHighlights {
  return {
    value: s,
    parts: [{
      value: s,
      highlight: false,
    }]
  };
}

// FlowPicker shows either readonly input or autocomplete input, depending
// on whether a flow is selected. This is due to different stylings of
// both components.
enum InputToShow {
  READONLY,
  AUTOCOMPLETE,
}

/**
 * Component that displays available Flows.
 */
@Component({
  selector: 'flow-picker',
  templateUrl: './flow_picker.ng.html',
  styleUrls: ['./flow_picker.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowPicker implements AfterViewInit, OnDestroy {
  private readonly unsubscribe$ = new Subject<void>();

  readonly flowsByCategory$ = this.flowListItemService.flowsByCategory$;

  private readonly flowsByName$: Observable<ReadonlyMap<string, FlowListItem>> =
      this.flowsByCategory$.pipe(map(
          fbc => new Map(
              Array.from(fbc.values()).flat().map(fli => [fli.name, fli]))));

  // Matcher used to filter flows by title.
  private readonly flowTitlesMatcher$: Observable<FuzzyMatcher> =
      this.flowsByCategory$.pipe(
          map(fbc => new FuzzyMatcher(
                  Array.from(fbc.values()).flat().map(f => f.friendlyName))));
  // Matcher used to filter flows by category.
  private readonly flowCategoriesMatcher$: Observable<FuzzyMatcher> =
      this.flowsByCategory$.pipe(
          map(fbc => new FuzzyMatcher(Array.from(fbc.keys()))));

  // selectedFlow$ emits a value every time a flow is selected. undefined
  // is emitted whenever selection is cleared (and is also the default value).
  readonly selectedFlow$ =
      new BehaviorSubject<FlowListItem|undefined>(undefined);

  readonly textInput = new FormControl('');
  readonly textInputWidth$ = new Subject<number>();


  private readonly textInputFocused$ = new Subject<boolean>();

  readonly commonFlows$: Observable<ReadonlyArray<FlowListItem>> =
      this.flowListItemService.commonFlowNames$.pipe(
          withLatestFrom(this.flowsByCategory$),
          map(([fNames, flowsByCategory]) => {
            const result = Array.from(flowsByCategory.values())
                               .flat()
                               .filter(fli => fNames.includes(fli.name));
            result.sort((a, b) => a.friendlyName.localeCompare(b.friendlyName));
            return result;
          }),
      );

  @ViewChild(MatAutocompleteTrigger, {static: false})
  autocompleteTrigger!: MatAutocompleteTrigger;

  @ViewChild('textInputElement')
  textInputElement!: ElementRef<HTMLInputElement>;

  private readonly textInput$: Observable<string> =
      this.textInput.valueChanges.pipe(
          startWith(''),
          filter(isNonNull),
          map(v => {
            // Autocomplete sends in a string when user types text in, and
            // a selected value whenever one is selected. Thus we have to
            // use reflection to determine the correct type.
            if (typeof v === 'string') {
              return v;
            } else {
              return (v as FlowListItem).friendlyName;
            }
          }),
      );

  readonly inputToShowEnum = InputToShow;

  readonly inputToShow$: Observable<InputToShow> = this.selectedFlow$.pipe(
      map(selectedFlow => {
        if (selectedFlow !== undefined) {
          return InputToShow.READONLY;
        } else {
          return InputToShow.AUTOCOMPLETE;
        }
      }),
  );

  // Subject synced with overlay's attach/detach events.
  readonly overviewOverlayAttached$ = new Subject<boolean>();

  // Subject used to force-hide the overview overlay.
  readonly overviewOverlayForceHidden$ = new Subject<void>();

  // When the input becomes empty or the input field gets focused while being
  // empty, the overview panel has to be attached. Whenever the input field is
  // non-empty, the overview panel has to be detached.
  //
  // Whenever the overview panel becomes detached, we have to make sure
  // overviewOverlayOpened$ is in sync and reports false - otherwise it
  // won't be attached correctly next time.
  readonly overviewOverlayOpened$: Observable<boolean> = merge(
      // If text input changes - emit true if it's empty and focused,
      // false otherwise.
      this.textInput$.pipe(
          withLatestFrom(this.textInputFocused$),
          map(([inputValue, isFocused]) => inputValue === '' && isFocused),
          ),
      // If text input becomes focused - emit true if it's empty.
      this.textInputFocused$.pipe(
          withLatestFrom(this.textInput$),
          filter(([isFocused, inputValue]) => inputValue === '' && isFocused),
          mapTo(true),
          ),
      // If the overlay becomes detached, emit false.
      this.overviewOverlayAttached$.pipe(
          filter(v => !v),
          ),
      // If the overlay is being forcibly hidden, pass-through the false
      // value.
      this.overviewOverlayForceHidden$.pipe(
          mapTo(true),
          ),
  );

  readonly autoCompleteCategories$:
      Observable<ReadonlyArray<FlowAutoCompleteCategory>> =
          this.textInput$.pipe(
              startWith(''),
              withLatestFrom(
                  this.flowsByCategory$, this.flowTitlesMatcher$,
                  this.flowCategoriesMatcher$),
              map(([v, flowsByCategory, titlesMatcher, categoriesMatcher]) =>
                      this.buildCategories(
                          v, flowsByCategory, titlesMatcher,
                          categoriesMatcher)),
          );


  private buildCategories(
      query: string, flowsByCategory: FlowsByCategory,
      titlesMatcher: FuzzyMatcher, categoriesMatcher: FuzzyMatcher):
      ReadonlyArray<FlowAutoCompleteCategory> {
    const acCategories: FlowAutoCompleteCategory[] = [];
    if (query === '') {
      return [];
    } else {
      const titleMatches = titlesMatcher.match(query);
      const titleMatchesMap = new Map(titleMatches.map(m => [m.subject, m]));
      const categoryMatches = categoriesMatcher.match(query);
      const categoryMatchesMap =
          new Map(categoryMatches.map(m => [m.subject, m]));

      for (const [category, items] of flowsByCategory) {
        const categoryMatch = categoryMatchesMap.get(category);
        const acOptions: FlowAutoCompleteOption[] = [];

        for (const item of items) {
          const titleMatch = titleMatchesMap.get(item.friendlyName);
          if (categoryMatch !== undefined || titleMatch !== undefined) {
            acOptions.push({
              title: titleMatch !== undefined ?
                  stringWithHighlightsFromMatch(titleMatch) :
                  stringWithHighlightsFromString(item.friendlyName),
              flowListItem: item,
            });
          }
        }

        if (acOptions.length > 0) {
          acOptions.sort((a, b) => a.title.value.localeCompare(b.title.value));
          acCategories.push({
            title: categoryMatch !== undefined ?
                stringWithHighlightsFromMatch(categoryMatch) :
                stringWithHighlightsFromString(category),
            options: acOptions,
          });
        }
      }
    }

    acCategories.sort((a, b) => a.title.value.localeCompare(b.title.value));
    return acCategories;
  }

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly flowListItemService: FlowListItemService,
  ) {
    this.clientPageFacade.selectedFlowDescriptor$
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(this.flowsByName$),
            )
        .subscribe(([fd, flowsByName]) => {
          const flowListItem = flowsByName.get(fd?.name ?? '');
          if (flowListItem !== undefined) {
            this.selectFlow(flowListItem);
          }
        });
  }

  trackCategory({}, category: FlowAutoCompleteCategory): string {
    return category.title.value;
  }

  trackOption({}, option: FlowAutoCompleteOption): string {
    return option.flowListItem.name;
  }

  displayWith(value: FlowListItem): string {
    return value.friendlyName;
  }

  selectFlow(fli: FlowListItem) {
    if (this.selectedFlow$.value === fli) {
      return;
    }
    this.textInput.setValue(fli.friendlyName);
    this.clientPageFacade.startFlowConfiguration(fli.name);
    this.autocompleteTrigger.closePanel();
    this.selectedFlow$.next(fli);
  }

  deselectFlow() {
    if (this.selectedFlow$.value === undefined) {
      return;
    }

    this.clientPageFacade.stopFlowConfiguration();
    this.selectedFlow$.next(undefined);

    this.textInput.setValue('');
    // clearInput() is called in the "clear button"'s click handler.
    // The autocomplete input field loses focus when the "clear button" is
    // clicked. However, the 'blur' event handler of the autocomplete input
    // is called after the click handler of the "clear button". Thus, we have
    // to call the openPanel() function after the current event handler
    // finishes.
    setTimeout(() => {
      this.autocompleteTrigger.openPanel();
      this.textInputElement.nativeElement.focus();
    }, 0);
  }

  clearInput() {
    this.textInput.setValue('');
  }

  overlayOutsideClick(event: MouseEvent) {
    // If the outside click lands on something other than the matAutocomplete
    // input, hide the overlay.
    if (event.target !== this.textInputElement.nativeElement) {
      this.overviewOverlayForceHidden$.next();
    }
  }

  ngAfterViewInit() {
    fromEvent(this.textInputElement.nativeElement, 'focus')
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(() => {
          this.textInputFocused$.next(true);
        });
    fromEvent(this.textInputElement.nativeElement, 'blur')
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(() => {
          this.textInputFocused$.next(false);
        });
    // Overlay seems to ignore first escape key press in certain
    // scenarios when used together with matAutocomplete. Making sure
    // the overlay is hidden when Esc is pressed.
    fromEvent(this.textInputElement.nativeElement, 'keydown', {capture: true})
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe((e: Event) => {
          if ((e as KeyboardEvent).key === 'Escape') {
            this.overviewOverlayAttached$.next(false);
          }
        });

    fromEvent(window, 'resize')
        .pipe(
            takeUntil(this.unsubscribe$),
            startWith(null),
            debounceTime(100),
            )
        .subscribe(() => {
          this.textInputWidth$.next(
              this.textInputElement.nativeElement.clientWidth);
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
