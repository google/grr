/*global Gallery,Dygraph,data */
Gallery.register(
  'no-range',
  {
    name: 'No Range',
    setup: function(parent) {
      parent.innerHTML = 
          "<p>Line should be visible in the middle of the chart:</p>" +
          "<div id='blah'></div>" +

          "<p>Line should be visible ~90% up the chart:</p>" +
          "<div id='blah2'></div>";
    },
    run: function() {
      new Dygraph(document.getElementById("blah"),
                  "X,Y\n10,12345\n11,12345\n",
                  { width: 640, height: 480 });
  
      new Dygraph(document.getElementById("blah2"),
          "date,10M\n" +
          "20021229,10000000.000000\n" +
          "20030105,10000000.000000\n" +
          "20030112,10000000.000000\n" +
          "20030119,10000000.000000\n" +
          "20030126,10000000.000000\n" +
          "20030202,10000000.000000\n" +
          "20030209,10000000.000000\n" +
          "20030216,10000000.000000\n",
          { width: 640, height: 480, includeZero: true, labelsKMB: true });
    }
  });
