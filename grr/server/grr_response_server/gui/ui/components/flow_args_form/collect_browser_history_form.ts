import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {map, shareReplay} from 'rxjs/operators';

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
    FlowArgumentForm<CollectBrowserHistoryArgs> implements OnInit {
  readonly form = new FormGroup({
    collectChrome: new FormControl(),
    collectFirefox: new FormControl(),
    collectInternetExplorer: new FormControl(),
    collectOpera: new FormControl(),
    collectSafari: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map((values: FormValues): CollectBrowserHistoryArgs => {
        const browsers = [];
        if (values.collectChrome) {
          browsers.push(CollectBrowserHistoryArgsBrowser.CHROME);
        }
        if (values.collectFirefox) {
          browsers.push(CollectBrowserHistoryArgsBrowser.FIREFOX);
        }
        if (values.collectInternetExplorer) {
          browsers.push(CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER);
        }
        if (values.collectOpera) {
          browsers.push(CollectBrowserHistoryArgsBrowser.OPERA);
        }
        if (values.collectSafari) {
          browsers.push(CollectBrowserHistoryArgsBrowser.SAFARI);
        }
        return {browsers};
      }), shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    const browsers = this.defaultFlowArgs.browsers ?? [];
    const fv: FormValues = {
      collectChrome:
          browsers.indexOf(CollectBrowserHistoryArgsBrowser.CHROME) !== -1,
      collectFirefox:
          browsers.indexOf(CollectBrowserHistoryArgsBrowser.FIREFOX) !== -1,
      collectInternetExplorer:
          browsers.indexOf(
              CollectBrowserHistoryArgsBrowser.INTERNET_EXPLORER) !== -1,
      collectOpera:
          browsers.indexOf(CollectBrowserHistoryArgsBrowser.OPERA) !== -1,
      collectSafari:
          browsers.indexOf(CollectBrowserHistoryArgsBrowser.SAFARI) !== -1,
    };
    this.form.patchValue(fv);
  }
}
