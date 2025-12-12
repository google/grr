import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  NgZone,
  signal,
  untracked,
} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatDividerModule} from '@angular/material/divider';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';
import {MatSelectModule} from '@angular/material/select';

import {
  ForemanClientRule,
  ForemanClientRuleSet,
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  ForemanIntegerClientRule,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanLabelClientRule,
  ForemanLabelClientRuleMatchMode,
  ForemanOsClientRule,
  ForemanRegexClientRule,
  ForemanRegexClientRuleForemanStringField,
} from '../../../lib/api/api_interfaces';
import {checkExhaustive} from '../../../lib/utils';
import {
  FriendlyForemanIntegerClientRulePipe,
  FriendlyForemanStringClientRulePipe,
} from '../../../pipes/fleet_collection_pipes/friendly_foreman_client_rule_pipe';
import {MarkdownPipe} from '../../../pipes/markdown/markdown_pipe';
import {SanitizerPipe} from '../../../pipes/sanitizer/sanitizer_pipe';
import {GlobalStore} from '../../../store/global_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleTitle,
} from '../collapsible_container';
import {
  ClientIntegerForm,
  ClientIntegerFormData,
} from './clients_form_subforms/client_integer_form';
import {
  ClientLabelsForm,
  ClientLabelsFormData,
} from './clients_form_subforms/client_labels_form';
import {
  ClientOsForm,
  ClientOsFormData,
} from './clients_form_subforms/client_os_form';
import {
  ClientRegexForm,
  ClientRegexFormData,
} from './clients_form_subforms/client_regex_form';

/**
 * Provides the forms for client rules.
 */
@Component({
  selector: 'clients-form',
  templateUrl: './clients_form.ng.html',
  styleUrls: ['./clients_form.scss'],
  imports: [
    ClientIntegerForm,
    ClientLabelsForm,
    ClientOsForm,
    ClientRegexForm,
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    FormsModule,
    FriendlyForemanIntegerClientRulePipe,
    FriendlyForemanStringClientRulePipe,
    MarkdownPipe,
    MatButtonModule,
    MatCardModule,
    MatDividerModule,
    MatIconModule,
    MatFormFieldModule,
    MatMenuModule,
    MatSelectModule,
    ReactiveFormsModule,
    SanitizerPipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientsForm {
  protected readonly globalStore = inject(GlobalStore);
  private readonly ngZone = inject(NgZone);

  initialRules = input.required<ForemanClientRuleSet>();

  protected readonly MatchMode = ForemanClientRuleSetMatchMode;
  protected readonly StringField = ForemanRegexClientRuleForemanStringField;
  protected readonly IntegerField = ForemanIntegerClientRuleForemanIntegerField;

  protected readonly presubmitFailed = signal<boolean>(false);

  protected readonly rulesMatchModeControl =
    new FormControl<ForemanClientRuleSetMatchMode>(
      ForemanClientRuleSetMatchMode.MATCH_ALL,
      {nonNullable: true},
    );
  protected ruleForms = signal<
    Array<
      | ClientLabelsFormData
      | ClientIntegerFormData
      | ClientRegexFormData
      | ClientOsFormData
    >
  >([]);

  warningMessage = computed(() => {
    const huntConfig = this.globalStore.uiConfig()?.huntConfig;
    if (!huntConfig) return null;

    return (
      `${huntConfig.presubmitWarningMessage} \n` +
      `To pass the check and run the fleet collection, you **MUST** adjust ` +
      `the configuration to one of the following options: \n` +
      `1. Explicitly exclude sensitive labels (recommended): \n ` +
      ` - Add a "Labels" rule with _Match Mode="Doesn't match any"_ and ` +
      `labels:  **[${huntConfig?.defaultExcludeLabels?.join(', ')}]**. \n` +
      ` - Set the overall _Match Mode_ to _Match ALL_. \n \n` +
      ` -- OR -- \n \n` +
      `\t - Click the "Fix" button to automatically configure these rules. \n` +
      `2. Disable the presubmit check: Add the following tag to the description: ` +
      `_'${huntConfig?.presubmitCheckWithSkipTag}\\=\\<reason\\>'_`
    );
  });

  constructor() {
    effect(() => {
      // Initialize the form state when the default values are available. We
      // need to use untracked here to avoid infinite change detection loop as
      // the `ruleForms` is updated and would again trigger the change
      // detection.
      if (this.initialRules()) {
        untracked(() => {
          this.resetInitialRules();
        });
      }
    });
  }

  protected addNewIntegerRule(data: ForemanIntegerClientRule) {
    this.ruleForms.update((rules) => [
      ...rules,
      new ClientIntegerFormData(data),
    ]);
  }

  protected addNewRegexRule(data: ForemanRegexClientRule) {
    this.ruleForms.update((rules) => [...rules, new ClientRegexFormData(data)]);
  }

  protected addNewLabelRule(data: ForemanLabelClientRule) {
    this.ruleForms.update((rules) => [
      ...rules,
      new ClientLabelsFormData(data, () => {
        this.ngZone.run(() => {
          this.presubmitCheck();
        });
      }),
    ]);
  }

  protected addNewOsRule(data: ForemanOsClientRule) {
    this.ruleForms.update((rules) => [...rules, new ClientOsFormData(data)]);
  }

  protected removeRule(index: number) {
    this.ruleForms.update((rules) =>
      rules.slice(0, index).concat(rules.slice(index + 1)),
    );
    this.presubmitCheck();
  }

  setFormState(rules: ForemanClientRuleSet) {
    if (rules?.matchMode) {
      this.rulesMatchModeControl.setValue(rules.matchMode);
    }

    const formData: Array<
      | ClientLabelsFormData
      | ClientIntegerFormData
      | ClientRegexFormData
      | ClientOsFormData
    > = [];
    for (const rule of rules.rules ?? []) {
      if (!rule.ruleType) continue;
      switch (rule.ruleType) {
        case ForemanClientRuleType.LABEL: {
          formData.push(
            new ClientLabelsFormData(rule.label ?? {}, () => {
              this.ngZone.run(() => {
                this.presubmitCheck();
              });
            }),
          );
          break;
        }
        case ForemanClientRuleType.INTEGER: {
          formData.push(new ClientIntegerFormData(rule.integer ?? {}));
          break;
        }
        case ForemanClientRuleType.REGEX: {
          formData.push(new ClientRegexFormData(rule.regex ?? {}));
          break;
        }
        case ForemanClientRuleType.OS: {
          formData.push(new ClientOsFormData(rule.os ?? {}));
          break;
        }
        default: {
          checkExhaustive(rule.ruleType);
        }
      }
    }
    this.ruleForms.set(formData);

    this.presubmitCheck();
  }

  getFormState(): ForemanClientRuleSet {
    const matchMode = this.rulesMatchModeControl.value ?? undefined;
    const rules: ForemanClientRule[] = [];
    for (const ruleForm of this.ruleForms()) {
      rules.push(ruleForm.getFormData());
    }
    return {matchMode, rules};
  }

  resetInitialRules() {
    this.setFormState(this.initialRules());
  }

  // Updates the presubmitFailed signal.
  presubmitCheck() {
    const expectedExcludedLabels =
      this.globalStore.uiConfig()?.huntConfig?.defaultExcludeLabels ?? [];
    if (expectedExcludedLabels.length === 0) {
      this.presubmitFailed.set(false);
      return;
    }

    const formData = this.getFormState();
    const rules = formData.rules;
    if (
      formData.matchMode !== ForemanClientRuleSetMatchMode.MATCH_ALL ||
      !rules
    ) {
      this.presubmitFailed.set(true);
      return;
    }

    const enforceExpectedLabels = rules.some((rule) => {
      if (rule.ruleType !== ForemanClientRuleType.LABEL) return false;
      if (!rule.label) return false;
      if (
        rule.label.matchMode !==
        ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY
      ) {
        return false;
      }
      for (const label of expectedExcludedLabels) {
        if (!rule.label.labelNames?.includes(label)) return false;
      }
      return true;
    });
    this.presubmitFailed.set(!enforceExpectedLabels);
  }

  fixPresubmit() {
    const expectedExcludedLabels =
      this.globalStore.uiConfig()?.huntConfig?.defaultExcludeLabels ?? [];
    this.rulesMatchModeControl.setValue(
      ForemanClientRuleSetMatchMode.MATCH_ALL,
    );
    this.addNewLabelRule({
      labelNames: expectedExcludedLabels,
      matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
    });
  }

  protected isClientOsFormData(
    data:
      | ClientOsFormData
      | ClientLabelsFormData
      | ClientRegexFormData
      | ClientIntegerFormData,
  ): data is ClientOsFormData {
    return data instanceof ClientOsFormData;
  }

  protected isClientLabelsFormData(
    data:
      | ClientOsFormData
      | ClientLabelsFormData
      | ClientRegexFormData
      | ClientIntegerFormData,
  ): data is ClientLabelsFormData {
    return data instanceof ClientLabelsFormData;
  }

  protected isClientRegexFormData(
    data:
      | ClientOsFormData
      | ClientLabelsFormData
      | ClientRegexFormData
      | ClientIntegerFormData,
  ): data is ClientRegexFormData {
    return data instanceof ClientRegexFormData;
  }

  protected isClientIntegerFormData(
    data:
      | ClientOsFormData
      | ClientLabelsFormData
      | ClientRegexFormData
      | ClientIntegerFormData,
  ): data is ClientIntegerFormData {
    return data instanceof ClientIntegerFormData;
  }
}
