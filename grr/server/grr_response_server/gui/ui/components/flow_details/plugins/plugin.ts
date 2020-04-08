import {Input} from '@angular/core';
import {FlowListEntry} from '@app/lib/models/flow';

/**
 * Base class for all flow details plugins.
 */
export abstract class Plugin {
  /**
   * Flow input binding containing flow data information to display.
   */
  @Input() flowListEntry!: FlowListEntry;
}
