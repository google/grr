import {ApiGrrUser} from '@app/lib/api/api_interfaces';
import {GrrUser} from '@app/lib/models/user';

/** Translates API ApiGrrUser object into the model's GrrUser. */
export function translateGrrUser(apiGrrUser: ApiGrrUser): GrrUser {
  if (!apiGrrUser.username) {
    throw new Error('username attribute is missing');
  }

  return {
    name: apiGrrUser.username,
  };
}
