import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {OnlineNotificationArgs} from '../../../lib/api/api_interfaces';
import {FormErrors, requiredInput} from '../form/form_validation';
import {Timestamp} from '../timestamp';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    email: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the OnlineNotification flow.
 */
@Component({
  selector: 'online-notification-form',
  templateUrl: './online_notification_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    SubmitButton,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnlineNotificationForm extends FlowArgsFormInterface<
  OnlineNotificationArgs,
  Controls
> {
  readonly clientLastSeenAt = input<Date | undefined>(undefined);

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: OnlineNotificationArgs,
  ): ControlValues<Controls> {
    return {
      email: flowArgs.email ?? this.controls.email.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): OnlineNotificationArgs {
    return formState;
  }
}
