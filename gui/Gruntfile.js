/**
 * Gruntfile for GRR UI frontend code.
 * @param {*} grunt
 */
module.exports = function(grunt) {

  var closureCompiler = require('superstartup-closure-compiler');

  // Find all mentioned third-party JS files in the base.html template file.
  // As order of these files is important, we can't use glob to concat them,
  // but have to rely on order specified in base.html.
  var getThirdPartyJsFiles = function() {
    var baseTemplate = grunt.file.read('templates/base.html');
    var re = /<script src="\/(static\/third-party\/.+\.js)"/gm;
    var result = [];

    while (match = re.exec(baseTemplate)) {
      if (match[1] != 'static/third-party/third-party.bundle.js') {
        result.push(match[1]);
      }

      re.lastIndex = match.index + 1;
    }

    return result;
  };

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    closureCompiler: {
      options: {
        compilerFile: closureCompiler.getPath(),
        compilerOpts: {
          language_in: 'ECMASCRIPT5',
          angular_pass: 'true',
          compilation_level: 'WHITESPACE_ONLY',
          create_source_map: 'static/grr-ui.bundle.js.map',
          summary_detail_level: 3,
          closure_entry_point: 'grrUi.appController.module',
          manage_closure_dependencies: 'true'
        }
      },
      // GRR UI Javascript sources are compiled via Closure compiler.
      compileUiBundleJs: {
        src: ['static/javascript/closure/base.js',
              'static/angular-components/**/*.js',
              '!static/angular-components/**/*_test.js'],
        dest: 'static/grr-ui.bundle.js'
      },
    },
    concat: {
      // GRR UI CSS sources are just concatenated.
      compileUiBundleCss: {
        src: ['static/css/**/*.css'],
        dest: 'static/grr-ui.bundle.css'
      },
      // Third-party JS files are concatenated in the order of their
      // appearance in base.html.
      compileThirdPartyBundleJs: {
        src: getThirdPartyJsFiles(),
        dest: 'static/third-party/third-party.bundle.js'
      },
      // Third-party CSS files are just concatenated.
      compileThirdPartyBundleCss: {
        src: ['static/third-party/**/*.css'],
        dest: 'static/third-party/third-party.bundle.css'
      }
    },
    closureDepsWriter: {
      options: {
        depswriter: '/usr/local/bin/depswriter.py',
        root_with_prefix: '"static/angular-components ../../angular-components"'
      },
      // GRR closure deps file is regenerated with depswriter.py.
      genDeps: {
        dest: 'static/javascript/closure/deps.js'
      }
    }
  });

  // "compile" task recompiles all dynamically generated files.
  grunt.registerTask('compile', ['closureCompiler:compileUiBundleJs',
                                 'concat:compileUiBundleCss',
                                 'concat:compileThirdPartyBundleJs',
                                 'concat:compileThirdPartyBundleCss',
                                 'closureDepsWriter:genDeps']);

  // Load closure compiler plugin.
  grunt.loadNpmTasks('grunt-closure-tools');

  // Load concat plugin.
  grunt.loadNpmTasks('grunt-contrib-concat');

  // Default task(s).
  grunt.registerTask('default', ['compile']);
};
