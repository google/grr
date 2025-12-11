import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {FileContentHarness} from '../../../shared/collection_results/data_renderer/file_results_table/testing/file_content_harness';
import {FileResultsTableHarness} from '../../../shared/collection_results/data_renderer/file_results_table/testing/file_results_table_harness';
import {CollapsibleContainerHarness} from '../../../shared/testing/collapsible_container_harness';

/** Harness for the FileExplorer component. */
export class FileExplorerHarness extends ComponentHarness {
  static hostSelector = 'file-explorer';

  searchFormField = this.locatorFor(
    MatFormFieldHarness.with({
      floatingLabelText: /.*Filter loaded paths by substring or regex match/,
    }),
  );

  fileResultsTable = this.locatorForOptional(FileResultsTableHarness);
  fileContent = this.locatorForOptional(FileContentHarness);

  listDirectoryButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'List directory'}),
  );
  listDirectoryAndSubdirectoriesButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'List directory & subdirectories'}),
  );
  downloadAllButton = this.locatorForOptional(
    MatButtonHarness.with({text: /.*Download all collected files & metadata/}),
  );

  async getCollapsibleContainers(
    nestedLevel: number,
  ): Promise<CollapsibleContainerHarness[]> {
    return this.locatorForAll(
      CollapsibleContainerHarness.with({
        selector: `.collapsible-container-${nestedLevel}`,
      }),
    )();
  }

  async getFolderNames(nestedLevel: number): Promise<string[]> {
    const locator = this.locatorForAll(`.folder-name-${nestedLevel}`);
    const nameDivs = await locator();
    return Promise.all(
      nameDivs.map(async (nameDiv) => {
        return nameDiv.text();
      }),
    );
  }

  async getOptionalRefreshButton(
    folderName: string,
  ): Promise<MatButtonHarness | null> {
    const locator = this.locatorForOptional(
      MatButtonHarness.with({
        selector: `[aria-label="refresh folder ${folderName}"]`,
        variant: 'icon',
        text: 'refresh',
      }),
    );
    return locator();
  }

  async getFileOrDirectoryButton(
    name: string,
  ): Promise<MatButtonHarness | null> {
    const locator = this.locatorForOptional(
      MatButtonHarness.with({text: new RegExp(`.*${name}.*`)}),
    );
    return locator();
  }

  async selectFileOrDirectory(name: string): Promise<void> {
    const button = await this.getFileOrDirectoryButton(name);
    if (!button) {
      throw new Error(`No file or directory button found for ${name}`);
    }
    await button.click();
  }

  async getSearchInput(): Promise<MatInputHarness> {
    const formField = await this.searchFormField();
    const input = await formField.getControl(MatInputHarness);
    if (!input) {
      throw new Error('No search input found');
    }
    return input;
  }
}
