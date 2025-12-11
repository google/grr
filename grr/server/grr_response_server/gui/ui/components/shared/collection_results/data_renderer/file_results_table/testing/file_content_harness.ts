import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {MatProgressSpinnerHarness} from '@angular/material/progress-spinner/testing';
import {MatTabHarness} from '@angular/material/tabs/testing';

import {HexViewHarness} from './hex_view_harness';
import {StatViewHarness} from './stat_view_harness';
import {TextViewHarness} from './text_view_harness';

/** Harness for the FileContent component. */
export class FileContentHarness extends ComponentHarness {
  static hostSelector = 'file-content';

  recollectButton = this.locatorForOptional(
    MatButtonHarness.with({text: /.*Recollect from client/}),
  );

  downloadButton = this.locatorFor(MatButtonHarness.with({text: /.*Download/}));

  hexView = this.locatorForOptional(HexViewHarness);
  statView = this.locatorForOptional(StatViewHarness);
  textView = this.locatorForOptional(TextViewHarness);

  loadMoreTextButton = this.locatorForOptional(
    MatButtonHarness.with({text: /.*Load More Text Content/}),
  );
  loadMoreHexButton = this.locatorForOptional(
    MatButtonHarness.with({text: /.*Load More Binary Content/}),
  );

  async getTab(label: string): Promise<MatTabHarness> {
    return this.locatorFor(MatTabHarness.with({label}))();
  }

  async getRecollectButtonIcon(): Promise<string | null> {
    const button = await this.recollectButton();
    if (!button) {
      throw new Error('Recollect button is not present');
    }
    return (await button.getHarness(MatIconHarness)).getName();
  }

  async hasRecollectButtonSpinner(): Promise<boolean> {
    const button = await this.recollectButton();
    if (!button) {
      throw new Error('Recollect button is not present');
    }
    return (await button.getHarnessOrNull(MatProgressSpinnerHarness)) != null;
  }

  async hasIsDirectoryMessage(): Promise<boolean> {
    return (await (await this.host()).text()).includes('Path is a directory');
  }

  async hasIsLoadingMessage(): Promise<boolean> {
    return (await (await this.host()).text()).includes('Loading path details');
  }

  async hasNoAccessMessage(): Promise<boolean> {
    return (await (await this.host()).text()).includes(
      'No access to the file, request client access.',
    );
  }
}
