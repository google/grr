import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {
  ForemanClientRule,
  ForemanClientRuleType,
  ForemanRegexClientRule,
  ForemanRegexClientRuleForemanStringField,
} from '../../../../lib/api/api_interfaces';
import {FriendlyForemanStringClientRulePipe} from '../../../../pipes/fleet_collection_pipes/friendly_foreman_client_rule_pipe';
import {ClientsFormData, ControlValues} from '../abstract_clients_form_data';

function makeControls() {
  return {
    regex: new FormControl<string>('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * Form data for client regex.
 */
export class ClientRegexFormData extends ClientsFormData<Controls> {
  override type = ForemanClientRuleType.REGEX;

  field: ForemanRegexClientRuleForemanStringField | undefined;

  constructor(data: ForemanRegexClientRule) {
    super();
    this.setFormData({ruleType: ForemanClientRuleType.REGEX, regex: data});
  }

  override makeControls() {
    return makeControls();
  }

  private setFormData(data: ForemanClientRule) {
    if (data.ruleType !== ForemanClientRuleType.REGEX) {
      throw new Error('Invalid rule type for regex form data');
    }
    this.field = data.regex?.field;
    this.controls.regex.setValue(data.regex?.attributeRegex ?? '');
  }

  override toClientRule(
    formControls: ControlValues<Controls>,
  ): ForemanClientRule {
    return {
      ruleType: ForemanClientRuleType.REGEX,
      regex: {
        field: this.field,
        attributeRegex: formControls.regex,
      },
    };
  }
}

/**
 * Provides the forms for client regex.
 */
@Component({
  selector: 'client-regex-form',
  templateUrl: './client_regex_form.ng.html',
  styleUrls: ['./client_regex_form.scss'],
  imports: [
    CommonModule,
    FormsModule,
    FriendlyForemanStringClientRulePipe,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientRegexForm {
  readonly regexData = input.required<
    ClientRegexFormData,
    ClientsFormData<Controls>
  >({
    transform: (data) => data as ClientRegexFormData,
  });

  protected readonly ForemanStringField =
    ForemanRegexClientRuleForemanStringField;
}
