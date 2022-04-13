import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser} from '../../lib/api/api_interfaces';

declare interface FormValues {
  collectChrome: boolean;
  collectFirefox: boolean;
  collectInternetExplorer: boolean;
  collectOpera: boolean;
  collectSafari: boolean;
}

/** Form that configures CollectBrowserHistory. */
@Component({
  selector: 'collect-browser-history-form',
  templateUrl: './collect_browser_history_form.ng.html',
  styleUrls: ['./collect_browser_history_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryForm extends
    FlowArgumentForm<CollectBrowserHistoryArgs, FormValues> {
  override makeControls(): Controls<FormValues> {
    return {
      collectChrome: new UntypedFormControl(),
      collectFirefox: new UntypedFormControl(),
      collectInternetExplorer: new UntypedFormControl(),
      collectOpera: new UntypedFormControl(),
      collectSafari: new UntypedFormControl(),
    };
  }

  override convertFlowArgsToFormState(flowArgs: CollectBrowserHistoryArgs):
      FormValues {
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

  override convertFormStateToFlowArgs(formState: FormValues):
      CollectBrowserHistoryArgs {
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
