import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';

import {
  Browser,
  CollectBrowserHistoryArgs,
} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    collectChromiumBasedBrowsers: new FormControl(true, {nonNullable: true}),
    collectFirefox: new FormControl(true, {nonNullable: true}),
    collectInternetExplorer: new FormControl(true, {nonNullable: true}),
    collectOpera: new FormControl(true, {nonNullable: true}),
    collectSafari: new FormControl(true, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures CollectBrowserHistory. */
@Component({
  selector: 'collect-browser-history-form',
  templateUrl: './collect_browser_history_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [CommonModule, MatCheckboxModule, ReactiveFormsModule, SubmitButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryForm extends FlowArgsFormInterface<
  CollectBrowserHistoryArgs,
  Controls
> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: CollectBrowserHistoryArgs) {
    const browsers = flowArgs.browsers ?? [];
    return {
      collectChromiumBasedBrowsers: browsers.includes(
        Browser.CHROMIUM_BASED_BROWSERS,
      ),
      collectFirefox: browsers.includes(Browser.FIREFOX),
      collectInternetExplorer: browsers.includes(Browser.INTERNET_EXPLORER),
      collectOpera: browsers.includes(Browser.OPERA),
      collectSafari: browsers.includes(Browser.SAFARI),
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    const browsers = [];
    if (formState.collectChromiumBasedBrowsers) {
      browsers.push(Browser.CHROMIUM_BASED_BROWSERS);
    }
    if (formState.collectFirefox) {
      browsers.push(Browser.FIREFOX);
    }
    if (formState.collectInternetExplorer) {
      browsers.push(Browser.INTERNET_EXPLORER);
    }
    if (formState.collectOpera) {
      browsers.push(Browser.OPERA);
    }
    if (formState.collectSafari) {
      browsers.push(Browser.SAFARI);
    }
    return {browsers};
  }
}
