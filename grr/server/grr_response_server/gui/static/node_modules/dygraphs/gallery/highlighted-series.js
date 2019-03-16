/*global Gallery,Dygraph,data */
Gallery.register(
  'highlighted-series',
  {
    name: 'Highlight Closest Series',
    title: 'Interactive closest-series highlighting',
    setup: function(parent) {
      parent.innerHTML = "<div id='demo'></div>";
    },
    run: function() {
var getData = function(numSeries, numRows, isStacked) {
  var data = [];

  for (var j = 0; j < numRows; ++j) {
    data[j] = [j];
  }
  for (var i = 0; i < numSeries; ++i) {
    var val = 0;
    for (var j = 0; j < numRows; ++j) {
      if (isStacked) {
        val = Math.random();
      } else {
        val += Math.random() - 0.5;
      }
      data[j][i + 1] = val;
    }
  }
  return data;
};

var makeGraph = function(className, numSeries, numRows, isStacked) {
  var demo = document.getElementById('demo');
  var div = document.createElement('div');
  div.className = className;
  div.style.display = 'inline-block';
  div.style.margin = '4px';
  demo.appendChild(div);

  var labels = ['x'];
  for (var i = 0; i < numSeries; ++i) {
    var label = '' + i;
    label = 's' + '000'.substr(label.length) + label;
    labels[i + 1] = label;
  }
  var g = new Dygraph(
      div,
      getData(numSeries, numRows, isStacked),
      {
        width: 480,
        height: 320,
        labels: labels.slice(),
        stackedGraph: isStacked,

        highlightCircleSize: 2,
        strokeWidth: 1,
        strokeBorderWidth: isStacked ? null : 1,

        highlightSeriesOpts: {
          strokeWidth: 3,
          strokeBorderWidth: 1,
          highlightCircleSize: 5
        }
      });
  var onclick = function(ev) {
    if (g.isSeriesLocked()) {
      g.clearSelection();
    } else {
      g.setSelection(g.getSelection(), g.getHighlightSeries(), true);
    }
  };
  g.updateOptions({clickCallback: onclick}, true);
  g.setSelection(false, 's005');
  //console.log(g);
};

makeGraph("few", 20, 50, false);
makeGraph("few", 10, 20, true);
makeGraph("many", 75, 50, false);
makeGraph("many", 40, 50, true);
    }
  });
