import {ChangeDetectionStrategy, Component, HostBinding, HostListener} from '@angular/core';
import {UntypedFormControl, UntypedFormGroup} from '@angular/forms';

import {AnyObject, OutputPluginDescriptor} from '../../../../lib/api/api_interfaces';


/**
 * Provides the forms for new hunt configuration.
 */
@Component({
  selector: 'app-output-plugins-form',
  templateUrl: './output_plugins_form.ng.html',
  styleUrls: ['./output_plugins_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutputPluginsForm {
  readonly controls = {
  };
  readonly outputPluginsForm = new UntypedFormGroup(this.controls);

  buildOutputPlugins(): ReadonlyArray<OutputPluginDescriptor> {
    return [
    ];
  }

  @HostBinding('class.closed') hideContent = true;

  @HostListener('click')
  onClick(event: Event) {
    this.showContent(event);
  }

  toggleContent(event: Event) {
    this.hideContent = !this.hideContent;
    event.stopPropagation();
  }

  showContent(event: Event) {
    if (this.hideContent) {
      this.hideContent = false;
      event.stopPropagation();
    }
  }
}
