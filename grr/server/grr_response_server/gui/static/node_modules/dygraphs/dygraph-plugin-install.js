/*global Dygraph:false */

// This file defines the ordering of the plugins.
//
// The ordering is from most-general to most-specific.
// This means that, in an event cascade, plugins which have registered for that
// event will be called in reverse order.
//
// This is most relevant for plugins which register a layout event, e.g.
// Axes, Legend and ChartLabels.

Dygraph.PLUGINS.push(
  Dygraph.Plugins.Legend,
  Dygraph.Plugins.Axes,
  Dygraph.Plugins.RangeSelector, // Has to be before ChartLabels so that its callbacks are called after ChartLabels' callbacks.
  Dygraph.Plugins.ChartLabels,
  Dygraph.Plugins.Annotations,
  Dygraph.Plugins.Grid
);
