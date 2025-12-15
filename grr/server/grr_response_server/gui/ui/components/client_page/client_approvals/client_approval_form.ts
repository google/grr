import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  inject,
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

import {HumanReadableDurationPipe} from '../../../pipes/human_readable/human_readable_duration_pipe';
import {ClientStore} from '../../../store/client_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ApproverSuggestionSubform,
  createApproverSuggestionFormGroup,
} from '../../shared/approvals/approver_suggestion_subform';
import {DurationValueAccessor} from '../../shared/form/duration_input/duration_value_accessor';
import {
  FormErrors,
  maxValue,
  requiredInput,
} from '../../shared/form/form_validation';

/**
 * Component to request approval for a client.
 */
@Component({
  selector: 'client-approval-form',
  templateUrl: './client_approval_form.ng.html',
  styleUrls: ['./client_approval_form.scss'],
  imports: [
    ApproverSuggestionSubform,
    CommonModule,
    DurationValueAccessor,
    FormErrors,
    FormsModule,
    HumanReadableDurationPipe,
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
export class ClientApprovalForm {
  readonly globalStore = inject(GlobalStore);
  readonly clientStore = inject(ClientStore);

  protected submitted = false;

  readonly controls = {
    reason: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    ccEnabled: new FormControl(true),
    approversForm: createApproverSuggestionFormGroup(),
    accessDuration: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput()],
    }),
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

    effect(() => {
      const maxAccessDurationSeconds =
        this.globalStore.uiConfig()?.maxAccessDurationSeconds;
      if (maxAccessDurationSeconds) {
        this.controls.accessDuration.setValidators([
          requiredInput(),
          maxValue(maxAccessDurationSeconds),
        ]);
      }
    });

    const initializeDefaultAccessDuration = effect(() => {
      const defaultAccessDurationSeconds =
        this.globalStore.uiConfig()?.defaultAccessDurationSeconds;
      if (defaultAccessDurationSeconds) {
        this.controls.accessDuration.setValue(defaultAccessDurationSeconds);

        initializeDefaultAccessDuration.destroy();
      }
    });
  }

  protected submit() {
    const clientId = this.clientStore.clientId();
    if (!clientId) {
      throw new Error('Client ID is not available');
    }
    const optionalCcEmail = this.globalStore.approvalConfig()?.optionalCcEmail;

    this.clientStore.requestClientApproval(
      this.controls.reason.value,
      this.controls.approversForm.value.approvers ?? [],
      this.controls.accessDuration.value,
      this.controls.ccEnabled.value && optionalCcEmail ? [optionalCcEmail] : [],
    );

    this.submitted = true;
  }
}
