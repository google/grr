import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {Any, EmailOutputPluginArgs} from '../../../../lib/api/api_interfaces';
import {OutputPluginType} from '../../../../lib/models/output_plugin';
import {OutputPluginData} from '../abstract_output_plugin_form_data';

/**
 * Class for manging the Email output plugin form data.
 */
export class EmailOutputPluginData extends OutputPluginData<EmailOutputPluginArgs> {
  override readonly prettyName = 'E-mail';
  override readonly pluginType = OutputPluginType.EMAIL;

  emailAddress: FormControl<string>;

  constructor(args: Any | undefined) {
    super();

    const emailAddress = (args as EmailOutputPluginArgs)?.emailAddress;
    this.emailAddress = new FormControl(emailAddress ?? '', {
      nonNullable: true,
    });
  }

  override getPluginArgs(): EmailOutputPluginArgs {
    return {
      emailAddress: this.emailAddress.value ?? '',
    };
  }
}

/**
 * Component for configuring the Email output plugin.
 */
@Component({
  selector: 'email-output-plugin-form',
  templateUrl: './email_output_plugin_form.ng.html',
  styleUrls: ['./email_output_plugin_form.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmailOutputPluginForm {
  readonly plugin = input.required<
    EmailOutputPluginData,
    OutputPluginData<EmailOutputPluginArgs>
  >({
    transform: (plugin) => plugin as EmailOutputPluginData,
  });
}
