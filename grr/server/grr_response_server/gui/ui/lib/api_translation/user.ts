import {ApiGrrUser} from '@app/lib/api/api_interfaces';
import {GrrUser} from '@app/lib/models/user';
import {assertKeyTruthy} from '../preconditions';

/** Translates API ApiGrrUser object into the model's GrrUser. */
export function translateGrrUser(apiGrrUser: ApiGrrUser): GrrUser {
  assertKeyTruthy(apiGrrUser, 'username');

  return {
    name: apiGrrUser.username,
  };
}
