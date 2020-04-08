import {translateGrrUser} from '@app/lib/api_translation/user';
import {initTestEnvironment} from '@app/testing';

initTestEnvironment();

describe('User API translation', () => {
  it('converts ApiGrrUser to GrrUser correctly', () => {
    expect(translateGrrUser({
      username: 'test',
    })).toEqual({
      name: 'test',
    });
  });
});
