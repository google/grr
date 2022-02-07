import {compareAlphabeticallyBy} from './type_utils';

/**
 * Every string that matches a user-input provides a list of ranges
 * corresponding to substrings that triggered the match. MatchRange
 * expresses one such range as [start, end).
 */
export type MatchRange = [number, number];

/**
 * Match encapsulates information about a match between a certain
 * user input and a string.
 */
export interface Match {
  /** Subject to match. */
  readonly subject: string;
  /** Character ranges inside subject that triggered the match. */
  readonly matchRanges: ReadonlyArray<MatchRange>;
}

/**
 * Find longest common prefix of 2 strings. For example: for
 * 'foo1' and 'foo bar', the longest common prefix will be 'foo'.
 */
function findLongestCommonPrefix(s1: string, s2: string): string {
  let i = 0;
  while (i < s1.length && i < s2.length && s1[i] === s2[i]) {
    i++;
  }
  return s1.substring(0, i);
}

/**
 * Recursive match helper function.
 *
 * @param currentComponent Current string component being matched.
 *     currentComponent === undefined means there are no more string
 *     components to check.
 * @param currentComponentOffset Offset of the currentComponent within
 *     the string. Used to calculate matched character ranges.
 * @param otherComponents String components that should be checked
 *     for a match after the currentComponent.
 * @param userInput A string containing a yet unmatched part of the user
 *     input.
 * @param matchedRanges Current list of matched ranges.
 */
function recursiveMatch(
    currentComponent: string|undefined, currentComponentOffset: number,
    otherComponents: string[], userInput: string,
    matchedRanges: MatchRange[]): MatchRange[]|undefined {
  // Empty user input means that all parts of it were removed when they
  // matched string components, meaning we have a successful match.
  if (!userInput) {
    return matchedRanges;
  }

  // Non-empty userInput and no more string components means a failed match.
  if (currentComponent === undefined) {
    return undefined;
  }

  const commonPrefix = findLongestCommonPrefix(currentComponent, userInput);
  // Generate all possible prefixes from the longest common prefix and
  // match them recursively.
  for (let j = commonPrefix.length; j > 0; --j) {
    const result = recursiveMatch(
        // Shift components by 1.
        otherComponents[0],
        currentComponentOffset + currentComponent.length + 1,
        otherComponents.slice(1),
        // Shift user input by the size of matched string and remove
        // trailing whitespace, if there's any.
        userInput.substring(j).trim(),
        // Update ranges with a newfound match.
        matchedRanges.concat(
            [[currentComponentOffset, currentComponentOffset + j]]));
    if (result !== undefined) {
      return result;
    }
  }

  // This code is reached only if all of the possible currentComponent's
  // prefixes didn't match the current userInput. In this case, try to
  // match same userInput to the next component.
  return recursiveMatch(
      otherComponents[0], currentComponentOffset + currentComponent.length + 1,
      otherComponents.slice(1), userInput, matchedRanges);
}


/**
 * Helper class for finding matching strings using prefix-based matching
 * algorithm.
 */
class PrefixMatchData {
  /* String components (done by splitting the title with ' '). */
  private readonly components: string[];
  /** A string containing first letter of every title component. */
  readonly firstLetters: string;

  constructor(subject: string) {
    this.components = subject.toLowerCase().split(' ');
    this.firstLetters = this.components.map(x => x[0]).join('');
  }

  /**
   * Matches a user input against the subject string.
   *
   * @return A list of MatchRanges if there's a match or undefined
   *     otherwise.
   */
  match(input: string): MatchRange[]|undefined {
    return recursiveMatch(
        this.components[0], 0, this.components.slice(1), input.trim(), []);
  }
}

/**
 * An implementation of a fuzzy matching algorithm used to filter the list
 * of strings by fuzzy matching them to user input. See the
 * match() method documentation  for more details.
 */
export class FuzzyMatcher {
  private readonly prefixMatchMap = new Map<PrefixMatchData, string>();

  constructor(/** A list of strings to be checked against user input. */
              private readonly subjects: ReadonlyArray<string>) {
    for (const subject of this.subjects) {
      this.prefixMatchMap.set(new PrefixMatchData(subject), subject);
    }
  }

  /**
   * Matches user input against the list of strings using a simple substring
   * match. I.e. 'o b' will trigger a match against a string 'foo bar',
   * since 'o b' is a substring of 'foo bar'.
   */
  private matchAsSubstring(input: string): Match[] {
    const results: Match[] = [];

    for (const subject of this.subjects) {
      const index = subject.toLowerCase().indexOf(input);
      if (index !== -1) {
        results.push({
          subject,
          matchRanges: [
            [index, index + input.length],
          ]
        });
      }
    }

    return results;
  }

  /**
   * Does a preliminary filtering of PrefixMatchData - only the ones that
   * have at least one first letter mathching the first letter of the user
   * input are left. This is a minor optimization that limits the number
   * of PrefixMatchDatas used to do the full recursive matching.
   *
   * For example: if there's a string 'foo bar wah', then
   * its corresponding PrefixMatchData will have firstLetter set to 'fbw'.
   * Consequently, user input of 'abc' won't match such string, whereas
   * user input of 'black' will.
   */
  private matchByFirstInputLetter(input: string): PrefixMatchData[] {
    return Array.from(this.prefixMatchMap.keys())
        .filter(matchData => matchData.firstLetters.includes(input[0]));
  }

  /**
   * Matches user input against the list of strings using a prefix matching
   * algorithm.
   *
   * @param input is a user input string.
   * @param stringsToIgnore contains a set of strings that shouldn't be
   *     included into the results map. This argument is used to not waste
   *     cycles on checking strings that were already matched with a
   *     simple substring match.
   * @return A list of Match objects.
   */
  private matchAsPrefixes(input: string, stringsToIgnore: Set<string>):
      Match[] {
    const results: Match[] = [];

    const filtered = this.matchByFirstInputLetter(input).filter(matchData => {
      const subject = this.prefixMatchMap.get(matchData);
      if (subject === undefined) {
        throw new Error('subject can\'t be undefined at this point');
      }
      return !stringsToIgnore.has(subject);
    });

    for (const prefixMatchData of filtered) {
      const matchRanges = prefixMatchData.match(input);
      if (matchRanges) {
        const subject = this.prefixMatchMap.get(prefixMatchData);
        if (subject === undefined) {
          throw new Error('subject can\'t be undefined at this point');
        }
        results.push({
          subject,
          matchRanges,
        });
      }
    }

    return results;
  }

  /**
   * Matches the user input against the list of strings using a simple
   * substring-based matching approach and more complicated prefix-based
   * matching approach. If a string triggers both a substring-based match and a
   * prefix-based match, a substring one is preferred (this affects the
   * MatchRange list containing the indices of matched characters
   * returned in Match object).
   *
   * For every string, the matching algorithm is this:
   * 1. If the input is a substring of the string, report it as a
   *    match. I.e. 'bar' triggers the match for a string 'foo bar
   *    The reported matching range then is [4, 7].
   *
   * 2. If there's no direct substring match, do a prefix-based fuzzy match.
   *    User input is then treated as a list of prefixes. For example:
   *
   *    a. 'bw' matches 'black and white' because of `*b*lack and *w*hite`.
   *
   *    b. 'blaawh' matches 'black and white' because of
   *    `*bla*ck *a*nd *wh*ite`.
   *
   *    c. 'bl a' matched 'black and white' because of `*bl* *a*`. I.e. a
   *    space within user's input means that characters on the left and right
   *    side of it should prefix-match different string components.
   *
   * @return A list of Match objects sorted alphabetically, according
   * to subject strings.
   */
  match(input: string): Match[] {
    const lowerInput = input.toLowerCase();

    const substringMatches = this.matchAsSubstring(lowerInput);
    const prefixMatches = this.matchAsPrefixes(
        lowerInput, new Set(substringMatches.map(m => m.subject)));

    const results = [...substringMatches, ...prefixMatches];
    results.sort(compareAlphabeticallyBy(result => result.subject));

    return results;
  }
}

/**
 * StringWithHighlightsPart is a part of a string with highlights. Such a string
 * is comprised of multiple parts, each either highlighted or not.
 */
export interface StringWithHighlightsPart {
  readonly value: string;
  readonly highlight: boolean;
}

/**
 * StringWithHighlights is a string comprised of multiple parts, each either
 * highlighted or not.
 */
export interface StringWithHighlights {
  readonly value: string;
  readonly parts: ReadonlyArray<StringWithHighlightsPart>;
}

/**
 * Converts a given match produced by the FuzzyMatcher into a string with
 * highlights.
 */
export function stringWithHighlightsFromMatch(match: Match):
    StringWithHighlights {
  const parts: StringWithHighlightsPart[] = [];

  let i = 0;
  let currentRangeIndex = 0;
  while (i < match.subject.length) {
    // If all the match ranges were checked, add the rest of the string as
    // the last part and exit the loop.
    if (currentRangeIndex >= match.matchRanges.length) {
      parts.push({
        value: match.subject.substring(i),
        highlight: false,
      });
      break;
    }

    const currentRange = match.matchRanges[currentRangeIndex];
    if (currentRange[0] === i) {
      // If i equals to a beginning of a range, add it as a new part and
      // mark it as highlighted.
      parts.push({
        value: match.subject.substring(currentRange[0], currentRange[1]),
        highlight: true,
      });
      i = currentRange[1];
      currentRangeIndex += 1;
    } else {
      // If i doesn't equal to a beginning of a range, add a part that spans
      // from i to the beginning of next range.
      parts.push({
        value: match.subject.substring(i, currentRange[0]),
        highlight: false,
      });
      i = currentRange[0];
    }
  }

  return {
    value: match.subject,
    parts,
  };
}
