import {GlobComponentExplanation} from '../../models/glob_expression';
import * as apiInterfaces from '../api_interfaces';

/**
 * Constructs a GlobComponentExplanation object from the corresponding API data
 * structure.
 */
export function translateGlobComponentExplanation(
  globComponentExplanation: apiInterfaces.GlobComponentExplanation,
): GlobComponentExplanation {
  return {
    globExpression: globComponentExplanation.globExpression,
    examples: globComponentExplanation.examples,
  };
}
