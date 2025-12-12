import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatTooltipModule} from '@angular/material/tooltip';

/**
 * Submit button for a flow form.
 */
@Component({
  selector: 'submit-button',
  templateUrl: './submit_button.ng.html',
  styleUrls: ['./submit_button.scss'],
  imports: [MatButtonModule, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubmitButton {
  /**
   * Whether the submit button is enabled, e.g. when the form is invalid the
   * button should be disabled.
   */
  readonly enabled = input<boolean>(false);
}
