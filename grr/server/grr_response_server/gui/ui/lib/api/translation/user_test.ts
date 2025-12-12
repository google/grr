import {initTestEnvironment} from '../../../testing';
import {ApiGrrUserUserType} from '../api_interfaces';
import {translateGrrUser} from './user';

initTestEnvironment();

describe('User API translation', () => {
  describe('translateGrrUser', () => {
    it('converts all values correctly', () => {
      expect(
        translateGrrUser({
          username: 'test',
          settings: {canaryMode: true},
          userType: ApiGrrUserUserType.USER_TYPE_ADMIN,
        }),
      ).toEqual({
        name: 'test',
        canaryMode: true,
        isAdmin: true,
      });
    });

    it('converts default values correctly', () => {
      expect(
        translateGrrUser({
          username: 'test',
        }),
      ).toEqual({
        name: 'test',
        canaryMode: false,
        isAdmin: false,
      });
    });
  });
});
