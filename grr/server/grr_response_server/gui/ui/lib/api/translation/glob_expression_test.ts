import {initTestEnvironment} from '../../../testing';
import {GlobComponentExplanation} from '../../models/glob_expression';
import * as apiInterfaces from '../api_interfaces';
import {translateGlobComponentExplanation} from './glob_expression';

initTestEnvironment();

describe('GlobExpression API Translation', () => {
  it('converts all client fields correctly', () => {
    const api: apiInterfaces.GlobComponentExplanation = {
      globExpression: 'foo',
      examples: ['bar', 'baz'],
    };
    const result: GlobComponentExplanation = {
      globExpression: 'foo',
      examples: ['bar', 'baz'],
    };
    expect(translateGlobComponentExplanation(api)).toEqual(result);
  });
});
