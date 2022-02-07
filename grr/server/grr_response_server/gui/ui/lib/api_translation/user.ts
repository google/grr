import {ApiGrrUser, ApproverSuggestion} from '../../lib/api/api_interfaces';
import {GrrUser} from '../../lib/models/user';
import {assertKeyTruthy, isNonNull} from '../preconditions';

/** Translates API ApiGrrUser object into the model's GrrUser. */
export function translateGrrUser(apiGrrUser: ApiGrrUser): GrrUser {
  assertKeyTruthy(apiGrrUser, 'username');

  return {
    name: apiGrrUser.username,
    canaryMode: apiGrrUser.settings?.canaryMode ?? false,
    huntApprovalRequired:
        apiGrrUser.interfaceTraits?.huntApprovalRequired ?? false,
  };
}

/** Extracts usernames from API ApproverSuggestions. */
export function translateApproverSuggestions(
    suggestions: ReadonlyArray<ApproverSuggestion>): ReadonlyArray<string> {
  return suggestions.map(suggestion => suggestion.username).filter(isNonNull);
}
