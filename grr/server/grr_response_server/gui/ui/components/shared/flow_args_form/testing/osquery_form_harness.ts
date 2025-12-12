import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {
  MatChipGridHarness,
  MatChipHarness,
} from '@angular/material/chips/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the OsqueryForm component. */
export class OsqueryFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'osquery-form';

  private readonly queryFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'SQL query'}),
  );

  readonly browseTablesButton = this.locatorFor(
    MatButtonHarness.with({text: /Browse available tables.*/}),
  );

  /** Button to show file collection settings. */
  readonly fileCollectionSettingsButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Show file collection settings.*/}),
  );

  /** Button to hide file collection settings. */
  readonly hideFileCollectionSettingsButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Hide file collection settings.*/}),
  );

  private readonly collectionColumnsFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Columns for file collection',
    }),
  );

  /** Button to show low-level settings. */
  readonly lowLevelSettingsButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Show low-level settings.*/}),
  );

  /** Button to hide low-level settings. */
  readonly hideLowLevelSettingsButton = this.locatorForOptional(
    MatButtonHarness.with({text: /Hide low-level settings.*/}),
  );

  private readonly timeoutFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Timeout'}),
  );

  /** Checkbox to ignore stderr errors. */
  readonly ignoreStderrErrorsCheckbox = this.locatorForOptional(
    MatCheckboxHarness.with({name: 'ignore_stderr'}),
  );

  private readonly configurationPathFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Configuration Path'}),
  );

  private readonly configurationContentFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Configuration content'}),
  );

  private readonly formErrors = this.locatorForAll('mat-error');

  /** Sets the query. */
  async setQuery(query: string) {
    const queryFormField = await this.queryFormField();
    const control = await queryFormField.getControl(MatInputHarness);
    await control?.setValue(query);
  }

  /** Returns the query. */
  async getQuery(): Promise<string> {
    const queryFormField = await this.queryFormField();
    const control = await queryFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  /** Sets the file collection columns. */
  async setFileCollectionColumns(columns: string[]) {
    const collectionColumnsFormField = await this.collectionColumnsFormField();
    const control =
      await collectionColumnsFormField?.getControl(MatChipGridHarness);
    const input = await control?.getInput();
    for (const column of columns) {
      await input!.setValue(column);
      await input!.blur();
    }
  }

  /** Returns the file collection columns. */
  async getFileCollectionColumns(): Promise<string[]> {
    const collectionColumnsFormField = await this.collectionColumnsFormField();
    const control =
      await collectionColumnsFormField?.getControl(MatChipGridHarness);

    const rows = await control?.getRows();
    if (!rows) {
      return [];
    }
    return Promise.all(rows.map((row) => row.getText()));
  }

  async getFileCollectionChips(): Promise<MatChipHarness[]> {
    const collectionColumnsFormField = await this.collectionColumnsFormField();
    const control =
      await collectionColumnsFormField?.getControl(MatChipGridHarness);
    if (!control) {
      return [];
    }
    return control?.getRows();
  }

  async hasFileCollectionFormField(): Promise<boolean> {
    const collectionColumnsFormField = await this.collectionColumnsFormField();
    return !!collectionColumnsFormField;
  }

  /** Sets the timeout. */
  async setTimeout(timeout: string) {
    const timeoutFormField = await this.timeoutFormField();
    const control = await timeoutFormField?.getControl(MatInputHarness);
    await control?.setValue(timeout);
  }

  /** Returns the timeout. */
  async getTimeout(): Promise<string> {
    const timeoutFormField = await this.timeoutFormField();
    const control = await timeoutFormField?.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async hasTimeout(): Promise<boolean> {
    const timeoutFormField = await this.timeoutFormField();
    return !!timeoutFormField;
  }

  /** Sets the configuration path. */
  async setConfigurationPath(path: string): Promise<void> {
    const configurationPathFormField = await this.configurationPathFormField();
    const control =
      await configurationPathFormField?.getControl(MatInputHarness);
    await control?.setValue(path);
  }

  /** Returns the configuration path. */
  async getConfigurationPath(): Promise<string> {
    const configurationPathFormField = await this.configurationPathFormField();
    const control =
      await configurationPathFormField?.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  /** Returns the configuration path warnings. */
  async getConfigurationPathWarnings(): Promise<string[]> {
    const configurationPathFormField = await this.configurationPathFormField();

    return configurationPathFormField?.getTextHints() ?? [];
  }

  /** Sets the configuration content. */
  async setConfigurationContent(content: string): Promise<void> {
    const configurationContentFormField =
      await this.configurationContentFormField();
    const control =
      await configurationContentFormField?.getControl(MatInputHarness);
    await control?.setValue(content);
  }

  /** Returns the configuration content. */
  async getConfigurationContent(): Promise<string> {
    const configurationContentFormField =
      await this.configurationContentFormField();
    const control =
      await configurationContentFormField?.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async getFormErrors(): Promise<string[]> {
    const formErrors = await this.formErrors();
    const errors = [];
    for (const formError of formErrors) {
      errors.push(await formError.text());
    }
    return errors;
  }
}
