import {CdkDrag, CdkDragHandle} from '@angular/cdk/drag-drop';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {
  FLOW_DETAILS_BY_TYPE,
  FlowCategory,
  FlowDetails,
} from '../../../lib/data/flows/flow_definitions';
import {Client} from '../../../lib/models/client';
import {FlowType} from '../../../lib/models/flow';
import {FriendlyFlowNamePipe} from '../../../pipes/flow_pipes/friendly_flow_name';
import {GlobalStore} from '../../../store/global_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../../shared/collapsible_container';
import {FlowArgsForm} from '../../shared/flow_args_form/flow_args_form';

/** Data passed to the dialog. */
export interface CreateFlowDialogData {
  flowType?: FlowType;
  flowArgs?: object;
  onSubmit: (
    flowName: string,
    flowArgs: object,
    disableRrgSupport: boolean,
  ) => void;
  client?: Client;
}

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'create-flow-dialog',
  templateUrl: './create_flow_dialog.ng.html',
  styleUrls: ['./create_flow_dialog.scss'],
  imports: [
    CdkDrag,
    CdkDragHandle,
    CollapsibleContainer,
    CollapsibleTitle,
    CollapsibleContent,
    CommonModule,
    FlowArgsForm,
    FriendlyFlowNamePipe,
    MatAutocompleteModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CreateFlowDialog {
  protected readonly globalStore = inject(GlobalStore);
  protected readonly dialogData: CreateFlowDialogData = inject(MAT_DIALOG_DATA);

  protected readonly disableRrgSupportControl = new FormControl<boolean>(
    false,
    {nonNullable: true},
  );

  protected readonly FLOW_DETAILS_BY_TYPE = FLOW_DETAILS_BY_TYPE;
  protected readonly CollapsibleState = CollapsibleState;

  protected readonly searchFlowType = new FormControl<string>('');
  protected readonly selectedFlowType = signal<FlowType | undefined>(undefined);

  protected flowCategories: FlowCategory[] = [];

  protected onSubmitInternal(flowName: string, flowArgs: object) {
    this.dialogData.onSubmit(
      flowName,
      flowArgs,
      this.disableRrgSupportControl.value,
    );
  }

  protected readonly onSubmitFn: (flowName: string, flowArgs: object) => void;

  constructor() {
    this.onSubmitFn = this.onSubmitInternal.bind(this);

    if (this.dialogData.flowType) {
      this.selectedFlowType.set(this.dialogData.flowType);
    }

    const categories = new Set<FlowCategory>();
    for (const flowDetails of FLOW_DETAILS_BY_TYPE.values()) {
      categories.add(flowDetails.category);
    }
    this.flowCategories = Array.from(categories).sort();
  }

  protected selectFlowType(flowType: FlowType) {
    this.selectedFlowType.set(flowType);
  }

  protected resetSelectedFlowType() {
    this.selectedFlowType.set(undefined);
    this.searchFlowType.reset();
  }

  protected matchesInput(flowDetails: FlowDetails, input: string) {
    return (
      flowDetails.friendlyName.toLowerCase().includes(input.toLowerCase()) ||
      flowDetails.category.toLowerCase().includes(input.toLowerCase()) ||
      flowDetails.description.toLowerCase().includes(input.toLowerCase())
    );
  }
}
