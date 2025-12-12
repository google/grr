import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';

import {GlobExpressionInputHarness} from '../../form/glob_expression_form_field/testing/glob_expression_input_harness';
import {ExtFlagsSubformHarness} from '../subforms/testing/ext_flags_subform_harness';
import {FileSizeRangeSubformHarness} from '../subforms/testing/file_size_range_subform_harness';
import {LiteralMatchSubformHarness} from '../subforms/testing/literal_match_subform_harness';
import {RegexMatchSubformHarness} from '../subforms/testing/regex_match_subform_harness';
import {TimeRangeSubformHarness} from '../subforms/testing/time_range_subform_harness';
import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the CollectMultipleFilesForm component. */
export class CollectMultipleFilesFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'collect-multiple-files-form';

  /** Glob expression inputs for the form. */
  readonly globExpressionInputs = this.locatorForAll(
    GlobExpressionInputHarness,
  );

  readonly addPathExpressionButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Add path expression/}),
  );

  readonly removePathExpressionButtons = this.locatorForAll(
    MatButtonHarness.with({variant: 'icon', text: /delete_outline/}),
  );

  readonly filterConditions = this.locatorForAll('.condition');

  readonly literalMatchFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Literal match filter/}),
  );
  readonly literalMatchSubform = this.locatorForOptional(
    LiteralMatchSubformHarness,
  );

  readonly regexMatchFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Regex match filter/}),
  );
  readonly regexMatchSubform = this.locatorForOptional(
    RegexMatchSubformHarness,
  );

  readonly modificationTimeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Modification time filter/}),
  );
  readonly modificationTimeSubform = this.locatorForOptional(
    TimeRangeSubformHarness.with({selector: '.modification-time-subform'}),
  );

  readonly accessTimeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Access time filter/}),
  );
  readonly accessTimeSubform = this.locatorForOptional(
    TimeRangeSubformHarness.with({selector: '.access-time-subform'}),
  );

  readonly inodeChangeTimeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Inode change time filter/}),
  );
  readonly inodeChangeTimeSubform = this.locatorForOptional(
    TimeRangeSubformHarness.with({selector: '.inode-change-time-subform'}),
  );

  readonly fileSizeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*File size filter/}),
  );
  readonly fileSizeSubform = this.locatorForOptional(
    FileSizeRangeSubformHarness,
  );

  readonly extFlagsFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Extended file flags filter/}),
  );
  readonly extFlagsSubform = this.locatorForOptional(ExtFlagsSubformHarness);

  async removePathExpression(index: number) {
    const removePathExpressionButtons =
      await this.removePathExpressionButtons();
    await removePathExpressionButtons[index].click();
  }

  async hasLiteralMatchSubform(): Promise<boolean> {
    return (await this.literalMatchSubform()) !== null;
  }

  async hasRegexMatchSubform(): Promise<boolean> {
    return (await this.regexMatchSubform()) !== null;
  }

  async hasModificationTimeSubform(): Promise<boolean> {
    return (await this.modificationTimeSubform()) !== null;
  }

  async hasAccessTimeSubform(): Promise<boolean> {
    return (await this.accessTimeSubform()) !== null;
  }

  async hasInodeChangeTimeSubform(): Promise<boolean> {
    return (await this.inodeChangeTimeSubform()) !== null;
  }

  async hasFileSizeSubform(): Promise<boolean> {
    return (await this.fileSizeSubform()) !== null;
  }

  async hasExtFlagsSubform(): Promise<boolean> {
    return (await this.extFlagsSubform()) !== null;
  }

  async isAddFilterButton(button: MatButtonHarness): Promise<boolean> {
    return button.hasHarness(MatIconHarness.with({name: 'add'}));
  }

  async isDeleteFilterButton(button: MatButtonHarness): Promise<boolean> {
    return button.hasHarness(MatIconHarness.with({name: 'delete'}));
  }
}
