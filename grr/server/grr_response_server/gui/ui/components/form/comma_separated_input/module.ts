import {NgModule} from '@angular/core';

import {CommaSeparatedNumberValueAccessor, CommaSeparatedValueAccessor} from './comma_separated_value_accessor';

/** Module for CommaSeparatedValueAccessor and related code. */
@NgModule({
  imports: [],
  declarations: [
    CommaSeparatedValueAccessor,
    CommaSeparatedNumberValueAccessor,
  ],
  exports: [
    CommaSeparatedValueAccessor,
    CommaSeparatedNumberValueAccessor,
  ],
})
export class CommaSeparatedInputModule {
}
