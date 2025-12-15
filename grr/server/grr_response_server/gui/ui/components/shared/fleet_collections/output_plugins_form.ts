import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';

import {Any} from '../../../lib/api/api_interfaces';
import {
  OutputPlugin,
  OutputPluginType,
} from '../../../lib/models/output_plugin';
import {GlobalStore} from '../../../store/global_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleTitle,
} from '../collapsible_container';
import {OutputPluginData} from './abstract_output_plugin_form_data';
import {
  EmailOutputPluginData,
  EmailOutputPluginForm,
} from './output_plugins_form_subforms/email_output_plugin_form';
import {checkExhaustive} from '../../../lib/utils';

const SUPPORTED_OUTPUT_PLUGINS: OutputPluginType[] = [
  OutputPluginType.EMAIL,
];

/**
 * Provides the forms for output plugins configuration.
 */
@Component({
  selector: 'output-plugins-form',
  templateUrl: './output_plugins_form.ng.html',
  styleUrls: ['./output_plugins_form.scss'],
  imports: [
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    EmailOutputPluginForm,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutputPluginsForm {
  protected readonly globalStore = inject(GlobalStore);

  initialOutputPlugins = input.required<readonly OutputPlugin[]>();
  disabled = input(false);

  protected readonly OutputPluginType = OutputPluginType;
  protected readonly checkExhaustive = checkExhaustive;

  protected readonly SUPPORTED_OUTPUT_PLUGINS = new Set(
    SUPPORTED_OUTPUT_PLUGINS,
  );

  protected readonly configuredOutputPlugins = signal<
    Array<OutputPluginData<{}>>
  >([]);

  constructor() {
    const initializeOutputPlugins = effect(() => {
      let initialized = false;
      for (const plugin of this.initialOutputPlugins()) {
        // Initialize the form state when the initial values are available. We
        // need to use untracked here to avoid infinite change detection loop as
        // the `configuredOutputPlugins` is updated and would again trigger the
        // change detection.
        untracked(() => {
          this.addOutputPlugin(plugin.pluginType, plugin.args);
          initialized = true;
        });
      }
      if (initialized) {
        initializeOutputPlugins.destroy();
      }
    });
  }

  protected addOutputPlugin(
    pluginType: OutputPluginType,
    args?: Any | undefined,
  ) {
    if (!this.SUPPORTED_OUTPUT_PLUGINS.has(pluginType)) {
      console.log('Unsupported output plugin: ', pluginType);
      return;
    }
    switch (pluginType) {
      case OutputPluginType.EMAIL:
        const emailPlugin = new EmailOutputPluginData(args);
        this.configuredOutputPlugins.set([
          ...this.configuredOutputPlugins(),
          emailPlugin,
        ]);
        break;
      default:
        console.log('Unknown plugin: ', pluginType);
    }
  }

  protected pluginIsAvailable(pluginType: OutputPluginType): boolean {
    return this.globalStore
      .outputPluginDescriptors()
      .some((plugin) => plugin.pluginType === pluginType);
  }

  protected removeOutputPlugin(index: number) {
    this.configuredOutputPlugins.update((plugins) =>
      plugins.slice(0, index).concat(plugins.slice(index + 1)),
    );
  }

  getFormState(): readonly OutputPlugin[] {
    const plugins: OutputPlugin[] = [];
    for (const plugin of this.configuredOutputPlugins()) {
      plugins.push(plugin.getPlugin());
    }
    return plugins;
  }
}
