import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

/** Harness for the NotFoundPage component. */
export class NotFoundPageHarness extends ComponentHarness {
  static hostSelector = 'not-found-page';

  readonly backButton = this.locatorFor(
    MatButtonHarness.with({text: /Go back/}),
  );

  readonly reportButton = this.locatorFor(
    MatButtonHarness.with({text: /Report the problem/}),
  );
}
