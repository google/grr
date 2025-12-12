import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {
  ForemanClientRule,
  ForemanClientRuleType,
  ForemanOsClientRule,
} from '../../../../lib/api/api_interfaces';
import {ClientsFormData, ControlValues} from '../abstract_clients_form_data';

function makeControls() {
  return {
    windows: new FormControl<boolean>(false, {nonNullable: true}),
    darwin: new FormControl<boolean>(false, {nonNullable: true}),
    linux: new FormControl<boolean>(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * Form data for client os.
 */
export class ClientOsFormData extends ClientsFormData<Controls> {
  override type = ForemanClientRuleType.OS;

  constructor(data: ForemanOsClientRule) {
    super();
    this.setFormData({ruleType: ForemanClientRuleType.OS, os: data});
  }

  override makeControls() {
    return makeControls();
  }

  private setFormData(data: ForemanClientRule) {
    if (data.ruleType !== ForemanClientRuleType.OS) {
      throw new Error('Invalid rule type for os form data');
    }
    this.controls.windows.setValue(data.os?.osWindows ?? false);
    this.controls.darwin.setValue(data.os?.osDarwin ?? false);
    this.controls.linux.setValue(data.os?.osLinux ?? false);
  }

  override toClientRule(
    formControls: ControlValues<Controls>,
  ): ForemanClientRule {
    return {
      ruleType: ForemanClientRuleType.OS,
      os: {
        osWindows: formControls.windows,
        osDarwin: formControls.darwin,
        osLinux: formControls.linux,
      },
    };
  }
}

/**
 * Provides the forms for client os.
 */
@Component({
  selector: 'client-os-form',
  templateUrl: './client_os_form.ng.html',
  styleUrls: ['./client_os_form.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientOsForm {
  readonly osData = input.required<ClientOsFormData, ClientsFormData<Controls>>(
    {
      transform: (data) => data as ClientOsFormData,
    },
  );
}
