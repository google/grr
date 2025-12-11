import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  input,
} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {ActivatedRoute} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ApproverSuggestionSubform,
  createApproverSuggestionFormGroup,
} from '../../shared/approvals/approver_suggestion_subform';
import {FormErrors, requiredInput} from '../../shared/form/form_validation';

/** Component that displays a form for requesting approval for fleet collection. */
@Component({
  selector: 'fleet-collection-approval-form',
  templateUrl: './fleet_collection_approval_form.ng.html',
  styleUrls: ['./fleet_collection_approval_form.scss'],
  imports: [
    ApproverSuggestionSubform,
    CommonModule,
    FormErrors,
    FormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionApprovalForm {
  readonly globalStore = inject(GlobalStore);
  readonly fleetCollectionStore = inject(FleetCollectionStore);
  private readonly httpApiService = inject(HttpApiWithTranslationService);

  readonly fleetCollectionId = input.required<string>();

  protected submitted = false;

  readonly controls = {
    reason: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    ccEnabled: new FormControl(true),
    approversForm: createApproverSuggestionFormGroup(),
  };
  readonly form = new FormGroup(this.controls);

  constructor() {
    inject(ActivatedRoute)
      .queryParams.pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe((params) => {
        const reason = params['reason'];
        if (reason) {
          this.controls.reason.patchValue(reason);
        }
      });
  }

  protected submit() {
    const optionalCcEmail = this.globalStore.approvalConfig()?.optionalCcEmail;

    this.fleetCollectionStore.requestFleetCollectionApproval(
      this.fleetCollectionId(),
      this.controls.reason.value,
      this.controls.approversForm.value.approvers ?? [],
      this.controls.ccEnabled.value && optionalCcEmail ? [optionalCcEmail] : [],
    );

    this.submitted = true;
  }
}
