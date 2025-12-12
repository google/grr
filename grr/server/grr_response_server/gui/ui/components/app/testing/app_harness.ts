import {ComponentHarness} from '@angular/cdk/testing';
import {MatProgressBarHarness} from '@angular/material/progress-bar/testing';
import {MatTabNavBarHarness} from '@angular/material/tabs/testing';

import {UserMenuHarness} from './user_menu_harness';

/** Harness for the App component. */
export class AppHarness extends ComponentHarness {
  static hostSelector = 'app-root';

  readonly userMenu = this.locatorFor(UserMenuHarness);

  readonly tabBar = this.locatorFor(MatTabNavBarHarness);

  readonly progressBar = this.locatorFor(MatProgressBarHarness);

  async isProgressBarVisible(): Promise<boolean> {
    const progressBar = await this.progressBar();
    const hostTestElement = await progressBar.host();
    // tslint:disable-next-line:no-any
    const nativeElement = (hostTestElement as any).element;

    return nativeElement.style.visibility === 'visible';
  }
}
