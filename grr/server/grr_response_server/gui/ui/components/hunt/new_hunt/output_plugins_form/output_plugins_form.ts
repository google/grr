import {ChangeDetectionStrategy, ChangeDetectorRef, Component, HostBinding, HostListener} from '@angular/core';
import {FormArray, FormBuilder, FormControl, FormGroup} from '@angular/forms';
import {take, tap} from 'rxjs/operators';

import {Any, OutputPluginDescriptor} from '../../../../lib/api/api_interfaces';
import {toStringFormControls} from '../../../../lib/form';
import {ConfigGlobalStore} from '../../../../store/config_global_store';


enum PluginType {
}

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
  readonly pluginType = PluginType;

  readonly outputPluginsForm = new FormGroup({});

  buildOutputPlugins(): readonly OutputPluginDescriptor[] {
    const res: OutputPluginDescriptor[] = [];
    for (const control of this.plugins.controls) {
      switch (control.get('type')!.value) {
        default: {
          break;
        }
      }
    }
    return res;
  }

  readonly fb = new FormBuilder();
  readonly plugins: FormArray<FormGroup> = this.fb.array([] as FormGroup[]);

  constructor(
      private readonly changeDetection: ChangeDetectorRef,
      private readonly configGlobalStore: ConfigGlobalStore) {
  }

  pluginGroup(pluginIndex: number): FormGroup {
    return this.plugins.at(pluginIndex);
  }

  addNewPlugin(type: PluginType) {
    switch (type) {
      default: {
        break;
      }
    }
    this.changeDetection.markForCheck();
  }

  removePlugin(pluginIndex: number) {
    this.plugins.removeAt(pluginIndex);
  }

  newTableForm(
      type: PluginType, name: string,
      annotations?: string[]|undefined): FormGroup {
    const defaultAnnotations = [new FormControl('', {nonNullable: true})];

    return this.fb.group({
      'type': [type],
      'name': [name],
      'annotations': this.fb.array(
          annotations ? toStringFormControls(annotations) : defaultAnnotations),
    });
  }

  setFormState(plugins: OutputPluginDescriptor[]) {
    if (plugins.length > 0) {
      this.plugins.clear();

      for (let i = 0; i < plugins.length; i++) {
        const plugin = plugins[i];
        switch (plugin.pluginName) {
          default: {
            break;
          }
        }
      }
    }
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
