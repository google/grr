import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  Injector,
  input,
  runInInjectionContext,
  Signal,
  signal,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {
  FormArray,
  FormControl,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';
import {MatSelectModule} from '@angular/material/select';

import {
  ForemanClientRule,
  ForemanClientRuleType,
  ForemanLabelClientRule,
  ForemanLabelClientRuleMatchMode,
} from '../../../../lib/api/api_interfaces';
import {GlobalStore} from '../../../../store/global_store';
import {ClientsFormData, ControlValues} from '../abstract_clients_form_data';

function makeControls() {
  return {
    labelMatchMode: new FormControl<ForemanLabelClientRuleMatchMode>(
      ForemanLabelClientRuleMatchMode.MATCH_ALL,
      {nonNullable: true},
    ),
    labelNames: new FormArray<FormControl<string>>([]),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * Form data for client labels.
 */
export class ClientLabelsFormData extends ClientsFormData<Controls> {
  override type = ForemanClientRuleType.LABEL;

  constructor(data: ForemanLabelClientRule, onChange: () => void) {
    super();
    this.setFormData({
      ruleType: ForemanClientRuleType.LABEL,
      label: data,
    });
    this.setOnChangeCallback(onChange);
  }

  override makeControls() {
    return makeControls();
  }

  private setFormData(data: ForemanClientRule) {
    if (data.ruleType !== ForemanClientRuleType.LABEL) {
      throw new Error('Invalid rule type for labels form data');
    }
    this.controls.labelNames.clear();
    for (const labelName of data.label?.labelNames ?? []) {
      this.controls.labelNames.push(
        new FormControl<string>(labelName, {nonNullable: true}),
      );
    }
    this.controls.labelMatchMode.setValue(
      data.label?.matchMode ?? ForemanLabelClientRuleMatchMode.MATCH_ALL,
    );
  }

  override toClientRule(
    formControls: ControlValues<Controls>,
  ): ForemanClientRule {
    return {
      ruleType: ForemanClientRuleType.LABEL,
      label: {
        labelNames: formControls.labelNames,
        matchMode: formControls.labelMatchMode,
      },
    };
  }

  addLabelName() {
    this.controls.labelNames.push(
      new FormControl<string>('', {nonNullable: true}),
    );
  }

  removeLabelName(index: number) {
    this.controls.labelNames.removeAt(index);
  }
}

/**
 * Provides the forms for client labels.
 */
@Component({
  selector: 'client-labels-form',
  templateUrl: './client_labels_form.ng.html',
  styleUrls: ['./client_labels_form.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatSelectModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientLabelsForm implements AfterViewInit {
  private readonly injector = inject(Injector);
  protected readonly globalStore = inject(GlobalStore);

  readonly labelsData = input.required<
    ClientLabelsFormData,
    ClientsFormData<Controls>
  >({
    transform: (data) => data as ClientLabelsFormData,
  });

  protected readonly MatchMode = ForemanLabelClientRuleMatchMode;

  protected formValues: Signal<Partial<ControlValues<Controls>> | undefined> =
    signal(undefined);

  ngAfterViewInit() {
    runInInjectionContext(this.injector, () => {
      this.formValues = toSignal(this.labelsData().form.valueChanges, {
        initialValue: this.labelsData().form.value,
      });

      effect(() => {
        if (this.formValues()) {
          this.labelsData().onChange!();
        }
      });
    });
  }
}
