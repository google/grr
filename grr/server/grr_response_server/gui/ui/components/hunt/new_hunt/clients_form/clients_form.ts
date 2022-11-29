import {ChangeDetectionStrategy, ChangeDetectorRef, Component, HostBinding, HostListener} from '@angular/core';
import {FormArray, FormBuilder, FormControl, FormGroup} from '@angular/forms';

import {ForemanClientRule, ForemanClientRuleSet, ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRule, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../../lib/api/api_interfaces';
import {toStringFormControls} from '../../../../lib/form';
import {ConfigGlobalStore} from '../../../../store/config_global_store';


type ForemanEnumValue = ForemanIntegerClientRuleForemanIntegerField|
    ForemanRegexClientRuleForemanStringField;

interface Rule {
  readonly name: string;
  readonly type: ForemanClientRuleType;
  readonly enumValue?: ForemanEnumValue;
}

const OS_DEFAULTS = {
  'Windows': false,
  'Darwin': false,
  'Linux': false,
} as const;

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
  readonly RuleSetMatchMode = ForemanClientRuleSetMatchMode;
  readonly operatingSystems = OS_DEFAULTS;
  readonly fb = new FormBuilder();
  readonly rulesMatchModeControl =
      new FormControl<ForemanClientRuleSetMatchMode>(
          this.RuleSetMatchMode.MATCH_ALL);
  readonly conditionsArray: FormArray<FormGroup> =
      this.fb.array([this.newOsForm('Operating System')]);
  readonly clientForm: FormGroup = this.fb.group({
    'rulesMatchMode': this.rulesMatchModeControl,
    'conditions': this.conditionsArray,
  });
  readonly commonRules: readonly Rule[] = [
    {
      name: 'Client Version',
      type: ForemanClientRuleType.INTEGER,
      enumValue: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION
    },
    {name: 'Label', type: ForemanClientRuleType.LABEL, enumValue: undefined},
    {
      name: 'Operating System',
      type: ForemanClientRuleType.OS,
      enumValue: undefined
    },
    {
      name: 'OS Version',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.OS_VERSION
    },
  ];
  readonly otherRules: readonly Rule[] = [
    {
      name: 'Client Clock',
      type: ForemanClientRuleType.INTEGER,
      enumValue: ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK
    },
    {
      name: 'Client Description',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION
    },
    {
      name: 'Client Labels',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_LABELS
    },
    {
      name: 'Client Name',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.CLIENT_NAME
    },
    {
      name: 'FQDN',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.FQDN
    },
    {
      name: 'Host IPs',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.HOST_IPS
    },
    {
      name: 'Install Time',
      type: ForemanClientRuleType.INTEGER,
      enumValue: ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME
    },
    {
      name: 'Kernel Version',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.KERNEL_VERSION
    },
    {
      name: 'Last Boot Time',
      type: ForemanClientRuleType.INTEGER,
      enumValue: ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME
    },
    {
      name: 'Mac Addresses',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES
    },
    {
      name: 'OS Release',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.OS_RELEASE
    },
    {
      name: 'System',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.SYSTEM
    },
    {
      name: 'Uname',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.UNAME
    },
    {
      name: 'User Names',
      type: ForemanClientRuleType.REGEX,
      enumValue: ForemanRegexClientRuleForemanStringField.USERNAMES
    },
  ];

  readonly matchMode = ForemanLabelClientRuleMatchMode;
  readonly clientRuleType = ForemanClientRuleType;
  readonly operator = ForemanIntegerClientRuleOperator;
  readonly allClientsLabels$ = this.configGlobalStore.clientsLabels$;

  constructor(
      private readonly changeDetection: ChangeDetectorRef,
      private readonly configGlobalStore: ConfigGlobalStore) {}

  conditions(): FormArray<FormGroup> {
    return this.conditionsArray;
  }

  conditionGroup(conditionIndex: number): FormGroup {
    return this.conditions().at(conditionIndex);
  }

  labelMatchMode(conditionIndex: number):
      FormControl<ForemanLabelClientRuleMatchMode> {
    return this.conditions().at(conditionIndex).get('matchMode') as
        FormControl<ForemanLabelClientRuleMatchMode>;
  }

  labelNames(conditionIndex: number): FormArray<FormControl<string>> {
    return this.conditions().at(conditionIndex).get('names') as
        FormArray<FormControl<string>>;
  }

  addLabelName(conditionIndex: number) {
    this.labelNames(conditionIndex).push(new FormControl('', {
      nonNullable: true
    }));
  }

  newLabelForm(
      name: string, matchMode?: ForemanLabelClientRuleMatchMode,
      names?: string[]|undefined): FormGroup {
    const defaultMode = this.matchMode.MATCH_ALL;
    const defaultNames = [new FormControl('', {nonNullable: true})];

    return this.fb.group({
      'type': [ForemanClientRuleType.LABEL],
      'name': [name],
      'matchMode':
          new FormControl(matchMode ?? defaultMode, {nonNullable: true}),
      'names':
          this.fb.array(names ? toStringFormControls(names) : defaultNames),
    });
  }

  osOptionGroup(conditionIndex: number): FormGroup {
    return this.conditions().at(conditionIndex).get('options') as FormGroup;
  }

  osOptionControl(conditionIndex: number, osName: string):
      FormControl<boolean> {
    return this.conditions().at(conditionIndex).get('options')?.get(osName) as
        FormControl<boolean>;
  }

  newOsForm(
      name: string,
      options?: {[key in keyof typeof OS_DEFAULTS]: boolean}): FormGroup {
    const osMap = options ?? this.operatingSystems;
    const operatingSystemsControls:
        {[key in keyof typeof osMap]: FormControl<boolean>} = Object.assign(
            {},
            ...Object.entries(osMap).map(([osName, osValue]) => ({
                                           [osName]: new FormControl<boolean>(
                                               osValue, {nonNullable: true})
                                         })));
    return this.fb.group({
      'type': [ForemanClientRuleType.OS],
      'name': [name],
      'options': this.fb.group(operatingSystemsControls),
    });
  }

  integerOperator(conditionIndex: number):
      FormControl<ForemanIntegerClientRuleOperator> {
    return this.conditions().at(conditionIndex).get('operator') as
        FormControl<ForemanIntegerClientRuleOperator>;
  }

  integerValue(conditionIndex: number): FormControl<bigint> {
    return this.conditions().at(conditionIndex).get('value') as
        FormControl<bigint>;
  }

  newIntegerForm(
      name: string,
      enumValue: ForemanIntegerClientRuleForemanIntegerField|
      ForemanRegexClientRuleForemanStringField|undefined,
      operator?: ForemanIntegerClientRuleOperator, value?: bigint): FormGroup {
    return this.fb.group({
      'type': [ForemanClientRuleType.INTEGER],
      'name': [name],
      'operator': new FormControl<ForemanIntegerClientRuleOperator>(
          operator ?? this.operator.EQUAL, {nonNullable: true}),
      'value': new FormControl<bigint>(value ?? BigInt(0), {nonNullable: true}),
      'enumName': [enumValue],
    });
  }

  regexAttribute(conditionIndex: number): FormControl<string> {
    return this.conditionGroup(conditionIndex).get('attribute') as
        FormControl<string>;
  }

  newRegexForm(
      name: string,
      enumValue: ForemanIntegerClientRuleForemanIntegerField|
      ForemanRegexClientRuleForemanStringField|undefined,
      attribute?: string): FormGroup {
    return this.fb.group({
      'type': [ForemanClientRuleType.REGEX],
      'name': [name],
      'attribute': new FormControl(attribute ?? '', {nonNullable: true}),
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

  findName(type: ForemanClientRuleType, enumValue?: ForemanEnumValue|undefined):
      string {
    const allRules: Rule[] = [...this.commonRules, ...this.otherRules];

    for (const rule of allRules) {
      if (rule.type === type && rule.enumValue === enumValue) {
        return rule.name;
      }
    }

    return '';
  }

  setFormState(rules: ForemanClientRuleSet) {
    if (rules?.matchMode) {
      this.rulesMatchModeControl.setValue(rules.matchMode);
    }

    if (rules?.rules) {
      this.conditionsArray.clear();

      for (let i = 0; i < rules.rules.length; i++) {
        const rule = rules.rules[i];
        switch (rule.ruleType) {
          case ForemanClientRuleType.LABEL: {
            const ruleName = this.findName(ForemanClientRuleType.LABEL);
            const f = this.newLabelForm(
                ruleName, rule.label?.matchMode,
                rule.label?.labelNames ? [...rule.label?.labelNames] :
                                         undefined);
            this.conditions().push(f);
            break;
          }
          case ForemanClientRuleType.OS: {
            const ruleName = this.findName(ForemanClientRuleType.OS);
            const options = {
              'Windows': rule.os?.osWindows ?? false,
              'Linux': rule.os?.osLinux ?? false,
              'Darwin': rule.os?.osDarwin ?? false
            };
            const f = this.newOsForm(ruleName, options);
            this.conditions().push(f);
            break;
          }
          case ForemanClientRuleType.INTEGER: {
            const ruleName = this.findName(
                ForemanClientRuleType.INTEGER, rule.integer?.field);
            const f = this.newIntegerForm(
                ruleName, rule.integer?.field, rule.integer?.operator,
                BigInt(rule.integer?.value ?? 0));
            this.conditions().push(f);
            break;
          }
          case ForemanClientRuleType.REGEX: {
            const ruleName =
                this.findName(ForemanClientRuleType.REGEX, rule.regex?.field);
            const f = this.newRegexForm(
                ruleName, rule.integer?.field, rule.regex?.attributeRegex);
            this.conditions().push(f);
            break;
          }
          default: {
            break;
          }
        }
      }
    }
    this.changeDetection.markForCheck();
  }

  buildRules(): ForemanClientRuleSet {
    const matchMode = this.rulesMatchModeControl.value ?? undefined;

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

    return {
      matchMode,
      rules: rulesArray,
    };
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
