import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {Browser, CollectBrowserHistoryArgs} from '../../lib/api/api_interfaces';

function makeControls() {
  return {
    collectChrome: new FormControl(true, {nonNullable: true}),
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
  styleUrls: ['./collect_browser_history_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryForm extends
    FlowArgumentForm<CollectBrowserHistoryArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: CollectBrowserHistoryArgs) {
    const browsers = flowArgs.browsers ?? [];
    return {
      collectChrome: browsers.includes(Browser.CHROME),
      collectFirefox: browsers.includes(Browser.FIREFOX),
      collectInternetExplorer: browsers.includes(Browser.INTERNET_EXPLORER),
      collectOpera: browsers.includes(Browser.OPERA),
      collectSafari: browsers.includes(Browser.SAFARI),
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    const browsers = [];
    if (formState.collectChrome) {
      browsers.push(Browser.CHROME);
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
