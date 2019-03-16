/**
 * @fileoverview Tests for fastCanvasProxy, which drops superfluous segments.
 *
 * @author danvdk@gmail.com (Dan Vanderkam)
 */
var fastCanvasProxyTestCase = TestCase("fast-canvas-proxy");

fastCanvasProxyTestCase.prototype.setUp = function() {
};

fastCanvasProxyTestCase.prototype.tearDown = function() {
};

var fakeCanvasContext = {
  moveTo: function() {},
  lineTo: function() {},
  beginPath: function() {},
  closePath: function() {},
  fill: function() {},
  stroke: function() {}
}

function extractMoveToAndLineToCalls(proxy) {
  var calls = proxy.calls__;
  var out = [];
  for (var i = 0; i < calls.length; i++) {
    var c = calls[i];
    if (c.name == 'moveTo' || c.name == 'lineTo') {
      out.push([c.name, c.args[0], c.args[1]]);
    }
  }
  return out;
}

fastCanvasProxyTestCase.prototype.testExtraMoveTosElided = function() {
  var htx = new Proxy(fakeCanvasContext);
  var fastProxy = DygraphCanvasRenderer._fastCanvasProxy(htx);

  fastProxy.moveTo(1, 1);
  fastProxy.lineTo(2, 1);
  fastProxy.moveTo(2, 1);
  fastProxy.lineTo(3, 1);
  fastProxy.moveTo(3, 1);
  fastProxy.stroke();

  assertEquals([['moveTo', 1, 1],
                ['lineTo', 2, 1],
                ['lineTo', 3, 1]], extractMoveToAndLineToCalls(htx));
};

fastCanvasProxyTestCase.prototype.testConsecutiveMoveTosElided = function() {
  var htx = new Proxy(fakeCanvasContext);
  var fastProxy = DygraphCanvasRenderer._fastCanvasProxy(htx);

  fastProxy.moveTo(1, 1);
  fastProxy.lineTo(2, 1);
  fastProxy.moveTo(3, 1);
  fastProxy.moveTo(3.1, 2);
  fastProxy.moveTo(3.2, 3);
  fastProxy.stroke();

  assertEquals([['moveTo', 1, 1],
                ['lineTo', 2, 1],
                ['moveTo', 3.2, 3]], extractMoveToAndLineToCalls(htx));
};

fastCanvasProxyTestCase.prototype.testSuperfluousSegmentsElided = function() {
  var htx = new Proxy(fakeCanvasContext);
  var fastProxy = DygraphCanvasRenderer._fastCanvasProxy(htx);

  fastProxy.moveTo(0.6, 1);
  fastProxy.lineTo(0.7, 2);
  fastProxy.lineTo(0.8, 3);
  fastProxy.lineTo(0.9, 4);
  fastProxy.lineTo(1.0, 5);  // max for Math.round(x) == 1
  fastProxy.lineTo(1.1, 3);
  fastProxy.lineTo(1.2, 0);  // min for Math.round(x) == 1
  fastProxy.lineTo(1.3, 1);
  fastProxy.lineTo(1.4, 2);
  fastProxy.moveTo(1.4, 2);
  fastProxy.lineTo(1.5, 2);  // rounding up to 2
  fastProxy.moveTo(1.5, 2);
  fastProxy.lineTo(1.6, 3);
  fastProxy.moveTo(1.6, 3);
  fastProxy.lineTo(1.7, 30);  // max for Math.round(x) == 2
  fastProxy.moveTo(1.7, 30);
  fastProxy.lineTo(1.8, -30);  // min for Math.round(x) == 2
  fastProxy.moveTo(1.8, -30);
  fastProxy.lineTo(1.9, 0);
  fastProxy.moveTo(3, 0);  // dodge the "don't touch the last pixel" rule.
  fastProxy.stroke();

  assertEquals([['moveTo', 0.6, 1],
                ['lineTo', 1.0, 5],
                ['lineTo', 1.2, 0],
                ['lineTo', 1.7, 30],
                ['lineTo', 1.8, -30],
                ['moveTo', 3, 0]], extractMoveToAndLineToCalls(htx));
};
