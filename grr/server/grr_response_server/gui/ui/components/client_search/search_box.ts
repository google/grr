import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  signal,
  ViewChild,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {
  MatAutocompleteModule,
  MatAutocompleteTrigger,
} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {ActivatedRoute, Router, RouterModule} from '@angular/router';
import {debounceTime, distinctUntilChanged} from 'rxjs/operators';

import {isClientId} from '../../lib/models/client';
import {ClientSearchStore} from '../../store/client_search_store';
import {GlobalStore} from '../../store/global_store';
import {SubmitOnMetaEnterDirective} from '../shared/form/submit_on_meta_enter/submit_on_meta_enter_directive';
import {OnlineChip} from '../shared/online_chip';

/**
 * Search box component.
 */
@Component({
  selector: 'search-box',
  templateUrl: './search_box.ng.html',
  styleUrls: ['./search_box.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatAutocompleteModule,
    MatAutocompleteTrigger,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    OnlineChip,
    ReactiveFormsModule,
    SubmitOnMetaEnterDirective,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchBox implements AfterViewInit {
  private readonly globalStore = inject(GlobalStore);
  protected readonly clientSearchStore = inject(ClientSearchStore);
  @ViewChild('input') input!: ElementRef<HTMLInputElement>;

  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly queryParams = toSignal(this.route.queryParams);

  protected readonly approvalReason = signal<string | undefined>(undefined);

  readonly searchFormControl = new FormControl('', {
    nonNullable: true,
  });

  private readonly debouncedSearchValue = toSignal(
    this.searchFormControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
    ),
    {initialValue: ''},
  );

  protected readonly filteredLabels = computed(() => {
    const query = this.debouncedSearchValue();
    if (!query || !query.startsWith('label:')) {
      return [];
    }
    const labelQuery = query.substring('label:'.length);
    const trimmedQuery = labelQuery.trim();
    return this.globalStore
      .allLabels()
      .filter((label) => label.startsWith(trimmedQuery))
      .slice(0, 8);
  });

  constructor() {
    this.clientSearchStore.searchClients(this.debouncedSearchValue);

    effect(() => {
      const query = this.queryParams()?.['q'] ?? null;
      if (query) {
        this.searchFormControl.patchValue(query);
      }
    });

    effect(() => {
      this.approvalReason.set(this.queryParams()?.['reason'] ?? undefined);
    });
  }

  ngAfterViewInit() {
    this.input.nativeElement.focus();
  }

  protected search() {
    const searchQuery = this.searchFormControl.value.trim();
    if (!searchQuery) {
      return;
    }
    this.clientSearchStore.searchClients(searchQuery);

    this.router.navigate(['/clients'], {
      queryParams: {'q': searchQuery},
      queryParamsHandling: 'merge',
    });
  }

  protected selectOption(option: string) {
    if (isClientId(option)) {
      if (this.approvalReason() !== undefined) {
        this.router.navigate(['/clients', option, 'approvals'], {
          queryParams: {'reason': this.approvalReason()},
          queryParamsHandling: 'replace',
        });
      } else {
        this.router.navigate(['/clients', option]);
      }
    } else {
      this.router.navigate(['/clients'], {
        queryParams: {'q': option},
        queryParamsHandling: 'merge',
      });
    }
  }
}
