import {ActivatedRouteSnapshot, Data, Route} from '@angular/router';

/**
 * Data for tracking page view with Google Analytics.
 *
 *  We don't want to track any sensible information (e.g. client identification)
 *  when tracking page views. Thus, we add information on how to redact it
 *  together with the route.
 */
export declare interface AnalyticsPageView {
  pageTitle?: string;
  pagePath?: string;
}

/** Extra data to be passed around in Grr routes. */
export declare interface GrrRouteData extends Data {
  pageViewTracking?: AnalyticsPageView;
}

/** Same as Route, but with typed `data`. */
export declare interface GrrRoute extends Route {
  data?: GrrRouteData;
}

/** Same as ActivatedRouteSnapshot, but with typed `data`. */
export declare interface GrrActivatedRouteSnapshot
  extends ActivatedRouteSnapshot {
  data: GrrRouteData;
}

/** Returns a link to a flow, e.g. provides '#BASEURL/v2/clients/clientid/flow/flowid'. */
export function makeFlowLink(clientId = '', flowId = ''): string {
  let flowlink = '';
  const url = new URL(window.location.origin);
  flowlink = 'v2/clients/' + clientId + '/flows/' + flowId;
  return url.toString() + flowlink;
}
