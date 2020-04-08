import {ChangeDetectionStrategy, Component, Output} from '@angular/core';
import {Subject} from 'rxjs';

import {FlowArgumentForm} from './form_interface';

/** Fallback to display when no form is configured for a Flow. */
@Component({
  selector: 'browser-history-flow-form',
  template: '<p>Form for selected Flow has not been found</p>',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FallbackFlowArgsForm extends FlowArgumentForm<{}> {
  @Output() readonly formValues$ = new Subject<{}>();
}
