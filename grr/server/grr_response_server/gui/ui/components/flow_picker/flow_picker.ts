import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {MatAutocompleteTrigger} from '@angular/material/autocomplete';
import {FuzzyMatcher, StringWithHighlights, stringWithHighlightsFromMatch} from '@app/lib/fuzzy_matcher';
import {isNonNull} from '@app/lib/preconditions';
import {BehaviorSubject, combineLatest, fromEvent, Observable, Subject} from 'rxjs';
import {debounceTime, filter, map, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';
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

enum FocusState {
  FOCUSED,
  BLURRED,
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
  private readonly textInputFocus$ = new Subject<FocusState>();

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

  readonly overviewOverlayOpened$: Observable<boolean> =
      combineLatest([this.textInput$, this.textInputFocus$])
          .pipe(
              map(([v, focus]) => v === '' && focus === FocusState.FOCUSED),
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

  ngAfterViewInit() {
    fromEvent(this.textInputElement.nativeElement, 'focus')
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(() => {
          this.textInputFocus$.next(FocusState.FOCUSED);
        });
    fromEvent(this.textInputElement.nativeElement, 'blur')
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(() => {
          this.textInputFocus$.next(FocusState.BLURRED);
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
