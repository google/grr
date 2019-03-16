// Copyright (c) 2012 Google, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/** 
 * @fileoverview Source samples.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

"use strict";

var Samples = {};
Samples.data = [
  {
    id: "interestingShapes",
    title: "Interesting Shapes",
    data: function() {
      var zp = function(x) { if (x < 10) return "0"+x; else return x; };
      var r = "date,parabola,line,another line,sine wave\n";
      for (var i=1; i<=31; i++) {
        r += "201110" + zp(i);
        r += "," + 10*(i*(31-i));
        r += "," + 10*(8*i);
        r += "," + 10*(250 - 8*i);
        r += "," + 10*(125 + 125 * Math.sin(0.3*i));
        r += "\n";
      }
      return r;
    },
    options: {
      colors: [
        "rgb(51,204,204)",
        "rgb(255,100,100)",
        "#00DD55",
        "rgba(50,50,200,0.4)"
      ],
      labelsSeparateLines: true,
      labelsKMB: true,
      legend: 'always',
      width: 640,
      height: 480,
      title: 'Interesting Shapes',
      xlabel: 'Date',
      ylabel: 'Count',
      axisLineColor: 'white',
      drawXGrid: false,

// This indentation is intentional; do not fix.
      pointClickCallback: function() {
  alert("p-click!");
}
    }
  },
  
  {
    id: "sparse",
    title: "Sparse Data",
    data: [
      [ new Date("2009/12/01"), 10, 10, 10],
      [ new Date("2009/12/02"), 15, 11, 12],
      [ new Date("2009/12/03"), null, null, 12],
      [ new Date("2009/12/04"), 20, 14, null],
      [ new Date("2009/12/05"), 15, null, 17],
      [ new Date("2009/12/06"), 18, null, null],
      [ new Date("2009/12/07"), 12, 14, null]
    ],
    options: {
      labels: ["Date", "Series1", "Series2", "Series3"]
    }
  },
  
  {
    id: "manyPoints",
    title: "Dense Data",
    data: function() {
      var numPoints = 1000;
      var numSeries = 100;
  
      var data = [];
      var xmin = 0.0;
      var xmax = 2.0 * Math.PI;
      var adj = .5;
      var delta = (xmax - xmin) / (numPoints - 1);
  
      for (var i = 0; i < numPoints; ++i) {
        var x = xmin + delta * i;
        var elem = [ x ];
        for (var j = 0; j < numSeries; j++) {
          var y = Math.pow(Math.random() - Math.random(), 7);
          elem.push(y);
        }
        data[i] = elem;
      }
      return data;
    },
    options: {
      labelsSeparateLines: true,
      width: 640,
      height: 480,
      title: 'Many Points',
      axisLineColor: 'white',
    }
  },

  {
    id: "errorBars",
    title: "Error Bars",
    data: [
      [1, [10,  10, 100]],
      [2, [15,  20, 110]],
      [3, [10,  30, 100]],
      [4, [15,  40, 110]],
      [5, [10, 120, 100]],
      [6, [15,  50, 110]],
      [7, [10,  70, 100]],
      [8, [15,  90, 110]],
      [9, [10,  50, 100]]
    ],
    options: {
      customBars: true,
      errorBars: true
    }
  },

  {
    id: "perSeries",
    title: "Per Series Options",
    data: function() {
      var zp = function(x) { if (x < 10) return "0"+x; else return x; };
      var r = "date,parabola,line,another line,sine wave,sine wave2\n";
      for (var i=1; i<=31; i++) {
        r += "200610" + zp(i);
        r += "," + 10*(i*(31-i));
        r += "," + 10*(8*i);
        r += "," + 10*(250 - 8*i);
        r += "," + 10*(125 + 125 * Math.sin(0.3*i));
        r += "," + 10*(125 + 125 * Math.sin(0.3*i+Math.PI));
        r += "\n";
      }
      return r;
    },
    options: {
      strokeWidth: 2,
      series : {
        'parabola': {
          strokeWidth: 0.0,
          drawPoints: true,
          pointSize: 4,
          highlightCircleSize: 6
        },
        'line': {
          strokeWidth: 1.0,
          drawPoints: true,
          pointSize: 1.5
        },
        'sine wave': {
          strokeWidth: 3,
          highlightCircleSize: 10
        },
        'sine wave2': {
          strokePattern: [10, 2, 5, 2],
          strokeWidth: 2,
          highlightCircleSize: 3
        }
      }
    }
  }
];

Samples.indexOf = function(id) {
  for (var idx in Samples.data) {
    if (Samples.data[idx].id == id) {
      return idx;
    }
  }
  return null;
}
