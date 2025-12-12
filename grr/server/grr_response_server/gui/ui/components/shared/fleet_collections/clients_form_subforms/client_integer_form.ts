import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';

import {
  ForemanClientRule,
  ForemanClientRuleType,
  ForemanIntegerClientRule,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
} from '../../../../lib/api/api_interfaces';
import {FriendlyForemanIntegerClientRulePipe} from '../../../../pipes/fleet_collection_pipes/friendly_foreman_client_rule_pipe';
import {ClientsFormData, ControlValues} from '../abstract_clients_form_data';

function makeControls() {
  return {
    operator: new FormControl<ForemanIntegerClientRuleOperator>(
      ForemanIntegerClientRuleOperator.EQUAL,
      {nonNullable: true},
    ),
    value: new FormControl<string>('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * Form data for client integer value.
 */
export class ClientIntegerFormData extends ClientsFormData<Controls> {
  override type = ForemanClientRuleType.INTEGER;

  field: ForemanIntegerClientRuleForemanIntegerField | undefined;

  constructor(data: ForemanIntegerClientRule) {
    super();
    this.setFormData({
      ruleType: ForemanClientRuleType.INTEGER,
      integer: data,
    });
  }

  override makeControls() {
    return makeControls();
  }

  override toClientRule(
    formControls: ControlValues<Controls>,
  ): ForemanClientRule {
    return {
      ruleType: ForemanClientRuleType.INTEGER,
      integer: {
        operator: formControls.operator,
        value: formControls.value,
        field: this.field,
      },
    };
  }

  private setFormData(data: ForemanClientRule) {
    if (data.ruleType !== ForemanClientRuleType.INTEGER) {
      throw new Error('Invalid rule type for integer form data');
    }
    this.controls.operator.setValue(
      data.integer?.operator ?? ForemanIntegerClientRuleOperator.EQUAL,
    );
    this.controls.value.setValue(data.integer?.value ?? '');
    this.field = data.integer?.field;
  }
}

/**
 * Provides the forms for client integer value.
 */
@Component({
  selector: 'client-integer-form',
  templateUrl: './client_integer_form.ng.html',
  styleUrls: ['./client_integer_form.scss'],
  imports: [
    CommonModule,
    FormsModule,
    FriendlyForemanIntegerClientRulePipe,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientIntegerForm {
  readonly integerData = input.required<
    ClientIntegerFormData,
    ClientsFormData<Controls>
  >({
    transform: (data) => data as ClientIntegerFormData,
  });

  protected readonly RuleOperator = ForemanIntegerClientRuleOperator;
  protected readonly ForemanIntegerField =
    ForemanIntegerClientRuleForemanIntegerField;
}
