import {ChangeDetectionStrategy, Component, HostBinding, HostListener} from '@angular/core';
import {FormArray, FormBuilder, FormControl, FormGroup} from '@angular/forms';

import {ForemanClientRule, ForemanClientRuleSet, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRule, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../../lib/api/api_interfaces';
import {ConfigGlobalStore} from '../../../../store/config_global_store';


/**
 * Provides the forms for new hunt configuration.
 */
@Component({
  selector: 'app-clients-form',
  templateUrl: './clients_form.ng.html',
  styleUrls: ['./clients_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientsForm {
  readonly operatingSystems: ReadonlyArray<string> = [
    'Windows',
    'Darwin',
    'Linux',
  ];
  readonly fb = new FormBuilder();
  readonly clientForm: FormGroup = this.fb.group({
    'rulesMatchMode': ['Match All (and)'],
    'conditions': this.fb.array([this.newOsForm('Operating System')]),
  });
  readonly commonRules: ReadonlyArray<
      {readonly name: string, readonly type: ForemanClientRuleType, readonly enumValue: ForemanIntegerClientRuleForemanIntegerField|ForemanRegexClientRuleForemanStringField|undefined}> =
      [
        {name: 'Client Version', type: ForemanClientRuleType.INTEGER, enumValue: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION},
        {name: 'Label', type: ForemanClientRuleType.LABEL, enumValue: undefined},
        {name: 'Operating System', type: ForemanClientRuleType.OS, enumValue: undefined},
        {name: 'OS Version', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.OS_VERSION},
      ];
  readonly otherRules: ReadonlyArray<
      {readonly name: string, readonly type: ForemanClientRuleType, readonly enumValue: ForemanIntegerClientRuleForemanIntegerField|ForemanRegexClientRuleForemanStringField|undefined}> =
      [
        {name: 'Client Clock', type: ForemanClientRuleType.INTEGER, enumValue: ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK},
        {name: 'Client Description', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION},
        {name: 'Client Labels', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_LABELS},
        {name: 'Client Name', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_NAME},
        {name: 'FQDN', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.FQDN},
        {name: 'Host IPs', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.HOST_IPS},
        {name: 'Install Time', type: ForemanClientRuleType.INTEGER, enumValue: ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME},
        {name: 'Kernel Version', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.KERNEL_VERSION},
        {name: 'Last Boot Time', type: ForemanClientRuleType.INTEGER, enumValue: ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME},
        {name: 'Mac Addresses', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES},
        {name: 'OS Release', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.OS_RELEASE},
        {name: 'System', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.SYSTEM},
        {name: 'Uname', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.UNAME},
        {name: 'User Names', type: ForemanClientRuleType.REGEX, enumValue: ForemanRegexClientRuleForemanStringField.USERNAMES},
      ];

  readonly matchMode = ForemanLabelClientRuleMatchMode;
  readonly clientRuleType = ForemanClientRuleType;
  readonly operator = ForemanIntegerClientRuleOperator;
  readonly allClientsLabels$ = this.configGlobalStore.clientsLabels$;

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {}

  conditions(): FormArray {
    return this.clientForm.get('conditions') as FormArray;
  }

  labelNames(conditionIndex: number): FormArray {
    return this.conditions().at(conditionIndex).get('names') as FormArray;
  }

  addLabelName(conditionIndex: number) {
    this.labelNames(conditionIndex).push(new FormControl(''));
  }

  newLabelForm(name: string): FormGroup {
    return this.fb.group({
      'type': [ForemanClientRuleType.LABEL],
      'name': [name],
      'matchMode': [this.matchMode.MATCH_ALL],
      'names': this.fb.array([new FormControl('')]),
    });
  }

  newOsForm(name: string): FormGroup {
    const operatingSystemsAsForm = this.operatingSystems.reduce(
        (operatingSystemsAsForm, operatingSystems) =>
            ({...operatingSystemsAsForm, [operatingSystems]: false}),
        {});
    return this.fb.group({
      'type': [ForemanClientRuleType.OS],
      'name': [name],
      'options': this.fb.group(operatingSystemsAsForm),
    });
  }

  newIntegerForm(
      name: string,
      enumValue: ForemanIntegerClientRuleForemanIntegerField|
      ForemanRegexClientRuleForemanStringField|undefined): FormGroup {
    return this.fb.group({
      'type': [ForemanClientRuleType.INTEGER],
      'name': [name],
      'operator': [''],
      'value': [''],
      'enumName': [enumValue],
    });
  }

  newRegexForm(
      name: string,
      enumValue: ForemanIntegerClientRuleForemanIntegerField|
      ForemanRegexClientRuleForemanStringField|undefined): FormGroup {
    return this.fb.group({
      'type': [ForemanClientRuleType.REGEX],
      'name': [name],
      'attribute': [''],
      'enumName': [enumValue],
    });
  }

  addNewRule(
      name: string, type: ForemanClientRuleType,
      enumValue: ForemanIntegerClientRuleForemanIntegerField|
      ForemanRegexClientRuleForemanStringField|undefined) {
    switch (type) {
      case ForemanClientRuleType.LABEL: {
        this.conditions().push(this.newLabelForm(name));
        break;
      }
      case ForemanClientRuleType.OS: {
        this.conditions().push(this.newOsForm(name));
        break;
      }
      case ForemanClientRuleType.INTEGER: {
        this.conditions().push(this.newIntegerForm(name, enumValue));
        break;
      }
      case ForemanClientRuleType.REGEX: {
        this.conditions().push(this.newRegexForm(name, enumValue));
        break;
      }
      default: {
        break;
      }
    }
  }

  removeRule(conditionIndex: number) {
    this.conditions().removeAt(conditionIndex);
  }

  removeLabelName(conditionIndex: number, labelIndex: number) {
    this.labelNames(conditionIndex).removeAt(labelIndex);
  }

  buildRules(): ForemanClientRuleSet {
    const conditions = this.conditions();
    const rulesArray: ForemanClientRule[] = [];
    for (const control of conditions.controls) {
      switch (control.get('type')!.value) {
        case ForemanClientRuleType.LABEL: {
          const namesFormArray = control.get('names') as FormArray;
          const labelNames =
              namesFormArray.controls.map(formCtrl => formCtrl.value);
          const labelRule: ForemanLabelClientRule = {
            labelNames,
            matchMode: control.get('matchMode')!.value,
          };
          const rule: ForemanClientRule = {
            ruleType: ForemanClientRuleType.LABEL,
            label: labelRule,
          };
          rulesArray.push(rule);
          break;
        }
        case ForemanClientRuleType.OS: {
          const osWindows = control.get('options')!.get('Windows')!.value;
          const osLinux = control.get('options')!.get('Linux')!.value;
          const osDarwin = control.get('options')!.get('Darwin')!.value;
          const rule: ForemanClientRule = {
            ruleType: ForemanClientRuleType.OS,
            os: {osWindows, osLinux, osDarwin},
          };
          rulesArray.push(rule);
          break;
        }
        case ForemanClientRuleType.INTEGER: {
          const operator = control.get('operator')!.value;
          const value = control.get('value')!.value;
          const field = control.get('enumName')!.value;
          const rule: ForemanClientRule = {
            ruleType: ForemanClientRuleType.INTEGER,
            integer: {operator, value, field},
          };
          rulesArray.push(rule);
          break;
        }
        case ForemanClientRuleType.REGEX: {
          const field = control.get('enumName')!.value;
          const rule: ForemanClientRule = {
            ruleType: ForemanClientRuleType.REGEX,
            regex: {
              attributeRegex: control.get('attribute')!.value,
              field,
            },
          };
          rulesArray.push(rule);
          break;
        }
        default: {
          break;
        }
      }
    }
    return {rules: rulesArray};
  }


  @HostBinding('class.closed') hideContent = false;

  @HostListener('click')
  onClick(event: Event) {
    this.showContent(event);
  }

  toggleContent(event: Event) {
    this.hideContent = !this.hideContent;
    event.stopPropagation();
  }

  showContent(event: Event) {
    if (this.hideContent) {
      this.hideContent = false;
      event.stopPropagation();
    }
  }
}
