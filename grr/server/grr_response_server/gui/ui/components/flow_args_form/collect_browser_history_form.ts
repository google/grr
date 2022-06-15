import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser} from '../../lib/api/api_interfaces';

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
      collectChrome: browsers.includes(CollectBrowserHistoryArgsBrowser.CHROME),
      collectFirefox:
          browsers.includes(CollectBrowserHistoryArgsBrowser.FIREFOX),
      collectInternetExplorer:
          browsers.includes(CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER),
      collectOpera: browsers.includes(CollectBrowserHistoryArgsBrowser.OPERA),
      collectSafari: browsers.includes(CollectBrowserHistoryArgsBrowser.SAFARI),
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    const browsers = [];
    if (formState.collectChrome) {
      browsers.push(CollectBrowserHistoryArgsBrowser.CHROME);
    }
    if (formState.collectFirefox) {
      browsers.push(CollectBrowserHistoryArgsBrowser.FIREFOX);
    }
    if (formState.collectInternetExplorer) {
      browsers.push(CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER);
    }
    if (formState.collectOpera) {
      browsers.push(CollectBrowserHistoryArgsBrowser.OPERA);
    }
    if (formState.collectSafari) {
      browsers.push(CollectBrowserHistoryArgsBrowser.SAFARI);
    }
    return {browsers};
  }
}
