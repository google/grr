import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';

import {GlobExpressionInputHarness} from '../../form/glob_expression_form_field/testing/glob_expression_input_harness';
import {FormWarningsHarness} from '../../form/testing/form_validation_harness';
import {FileSizeRangeSubformHarness} from '../subforms/testing/file_size_range_subform_harness';
import {LiteralMatchSubformHarness} from '../subforms/testing/literal_match_subform_harness';
import {RegexMatchSubformHarness} from '../subforms/testing/regex_match_subform_harness';
import {TimeRangeSubformHarness} from '../subforms/testing/time_range_subform_harness';
import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ClientRegistryFinderForm component. */
export class ClientRegistryFinderFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'client-registry-finder-form';

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

  readonly windowsPathWarnings = this.locatorForAll(FormWarningsHarness);

  readonly filterConditions = this.locatorForAll('.condition');

  readonly addLiteralMatchFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Add literal match filter/}),
  );
  readonly removeLiteralMatchFilterButtons = this.locatorForAll(
    MatButtonHarness.with({text: /.*Remove literal match filter/}),
  );
  readonly literalMatchSubforms = this.locatorForAll(
    LiteralMatchSubformHarness,
  );

  readonly addRegexMatchFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Add regex match filter/}),
  );
  readonly removeRegexMatchFilterButtons = this.locatorForAll(
    MatButtonHarness.with({text: /.*Remove regex match filter/}),
  );
  readonly regexMatchSubforms = this.locatorForAll(RegexMatchSubformHarness);

  readonly addModificationTimeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Add modification time filter/}),
  );
  readonly removeModificationTimeFilterButtons = this.locatorForAll(
    MatButtonHarness.with({text: /.*Remove modification time filter/}),
  );
  readonly modificationTimeSubforms = this.locatorForAll(
    TimeRangeSubformHarness.with({selector: '.modification-time-subform'}),
  );

  readonly addFileSizeFilterButton = this.locatorFor(
    MatButtonHarness.with({text: /.*Add file size filter/}),
  );
  readonly removeFileSizeFilterButtons = this.locatorForAll(
    MatButtonHarness.with({text: /.*Remove file size filter/}),
  );
  readonly fileSizeSubforms = this.locatorForAll(FileSizeRangeSubformHarness);

  async removePathExpression(index: number) {
    const removePathExpressionButtons =
      await this.removePathExpressionButtons();
    await removePathExpressionButtons[index].click();
  }

  async removeLiteralMatchFilter(index: number) {
    const removeFilterButtons = await this.removeLiteralMatchFilterButtons();
    await removeFilterButtons[index].click();
  }

  async removeRegexMatchFilter(index: number) {
    const removeFilterButtons = await this.removeRegexMatchFilterButtons();
    await removeFilterButtons[index].click();
  }

  async removeModificationTimeFilter(index: number) {
    const removeFilterButtons =
      await this.removeModificationTimeFilterButtons();
    await removeFilterButtons[index].click();
  }

  async removeFileSizeFilter(index: number) {
    const removeFilterButtons = await this.removeFileSizeFilterButtons();
    await removeFilterButtons[index].click();
  }

  async numLiteralMatchSubforms(): Promise<number> {
    return (await this.literalMatchSubforms()).length;
  }

  async numRegexMatchSubforms(): Promise<number> {
    return (await this.regexMatchSubforms()).length;
  }

  async numModificationTimeSubforms(): Promise<number> {
    return (await this.modificationTimeSubforms()).length;
  }

  async numFileSizeSubforms(): Promise<number> {
    return (await this.fileSizeSubforms()).length;
  }

  async isAddFilterButton(button: MatButtonHarness): Promise<boolean> {
    return button.hasHarness(MatIconHarness.with({name: 'add'}));
  }

  async isDeleteFilterButton(button: MatButtonHarness): Promise<boolean> {
    return button.hasHarness(MatIconHarness.with({name: 'delete'}));
  }
}
