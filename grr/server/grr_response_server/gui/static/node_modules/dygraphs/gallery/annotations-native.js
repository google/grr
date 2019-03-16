/*global Gallery,Dygraph,data */
Gallery.register(
  'annotations-native',
  {
    name: 'Annotations with Native format',
    setup: function(parent) {
      parent.innerHTML =
        "<p>This test demonstrates how annotations can be used with " +
        "<a href='http://dygraphs.com/data.html#array'>native-format</a> data.</p>" +
        "<div id='demodiv'></div>";
    },
    run: function() {
      var g = new Dygraph(
              document.getElementById("demodiv"),
              [
                [ new Date("2011/11/01"), 100 ],
                [ new Date("2011/11/02"), 200 ],
                [ new Date("2011/11/03"), 300 ],
                [ new Date("2011/11/04"), 100 ],
                [ new Date("2011/11/05"), 200 ],
                [ new Date("2011/11/06"), 300 ],
                [ new Date("2011/11/07"), 200 ],
                [ new Date("2011/11/08"), 100 ]
              ],
              {
                labels: [ 'Date', 'Value' ]
              }
          );

      g.setAnnotations([{
        series: 'Value',
        x: Date.parse('2011/11/04'),
        shortText: 'M',
        text: 'Marker'
      }]);
  }
});
