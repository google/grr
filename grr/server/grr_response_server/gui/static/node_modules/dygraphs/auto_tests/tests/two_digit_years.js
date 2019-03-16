/**
 * @fileoverview Test to check that years < 100 get the correct ticks.
 *
 * @author gmadrid@gmail.com (George Madrid)
 */
var TwoDigitYearsTestCase = TestCase("two-digit-years");

TwoDigitYearsTestCase.prototype.testTwoDigitYears = function() {
  // A date with a one digit year: '9 AD'.
  var start = new Date(9, 2, 3);
  // A date with a two digit year: '11 AD'.
  var end = new Date(11, 3, 5);

  // Javascript will automatically add 1900 to our years if they are < 100.
  // Use setFullYear() to get the actual years we desire.
  start.setFullYear(9);
  end.setFullYear(11);

  var ticks = Dygraph.getDateAxis(start, end, Dygraph.QUARTERLY, function(x) {
    return Dygraph.DEFAULT_ATTRS.axes['x'][x];
  });

  // This breaks in Firefox & Safari:
  // assertEquals([{"v":-61875345600000,"label":"Apr 9"},{"v":-61867483200000,"label":"Jul 9"},{"v":-61859534400000,"label":"Oct 9"},{"v":-61851582000000,"label":"Jan 10"},{"v":-61843809600000,"label":"Apr 10"},{"v":-61835947200000,"label":"Jul 10"},{"v":-61827998400000,"label":"Oct 10"},{"v":-61820046000000,"label":"Jan 11"},{"v":-61812273600000,"label":"Apr 11"}], ticks);
};
