import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  signal,
} from '@angular/core';
import {
  ControlContainer,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {User} from '../user';

/** Subform that provides a form field for entering approvers. */
@Component({
  selector: 'approver-suggestion-subform',
  templateUrl: './approver_suggestion_subform.ng.html',
  styleUrls: ['./approver_suggestion_subform.scss'],
  imports: [
    CommonModule,
    MatAutocompleteModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApproverSuggestionSubform {
  private readonly httpApiService = inject(HttpApiWithTranslationService);
  protected readonly controlContainer = inject(ControlContainer);

  readonly separatorKeysCodes: number[] = [ENTER, COMMA, SPACE];

  readonly approverSuggestions = signal<readonly string[]>([]);

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createApproverSuggestionFormGroup
    >;
  }

  constructor() {
    effect(() => {
      this.formGroup.controls.input.valueChanges.subscribe((value) => {
        this.httpApiService
          .suggestApprovers(value ?? '')
          .subscribe((approverSuggestions) => {
            // Remove already selected approvers from the suggestions.
            approverSuggestions = approverSuggestions.filter(
              (approver) =>
                !this.formGroup.controls.approvers.value.includes(approver),
            );
            this.approverSuggestions.set(approverSuggestions);
          });
      });
    });
  }

  protected addRequestedApprover(username: string) {
    this.formGroup.controls.approvers.value.push(username);
    this.formGroup.controls.input.setValue('');
  }

  protected tryAddRequestedApprover(
    username: string,
    inputEl: HTMLInputElement,
  ) {
    const formApprovers = this.formGroup.controls.approvers.value;
    if (formApprovers.includes(username)) {
      return;
    }
    if (this.approverSuggestions().includes(username)) {
      this.addRequestedApprover(username);
      inputEl.value = '';
    }
  }

  protected removeRequestedApprover(username: string) {
    const formApprovers = this.formGroup.controls.approvers.value;
    if (!formApprovers.includes(username)) {
      return;
    }
    this.formGroup.controls.approvers.value?.splice(
      formApprovers.indexOf(username),
      1,
    );
  }
}

/** Initializes a form group corresponding to the approver suggestion. */
export function createApproverSuggestionFormGroup() {
  const approvers = new FormControl<string[]>([], {nonNullable: true});
  const input = new FormControl<string>('', {nonNullable: true});

  return new FormGroup({approvers, input});
}
