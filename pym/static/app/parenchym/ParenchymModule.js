'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _angular = require('angular');

var _angular2 = _interopRequireDefault(_angular);

var _StickyBreadcrumbsService = require('./StickyBreadcrumbsService');

var _StickyBreadcrumbsService2 = _interopRequireDefault(_StickyBreadcrumbsService);

var _RecursionHelper = require('./RecursionHelper');

var _RecursionHelper2 = _interopRequireDefault(_RecursionHelper);

var _StickyBreadcrumbsDirective = require('./StickyBreadcrumbsDirective');

var _StickyBreadcrumbsDirective2 = _interopRequireDefault(_StickyBreadcrumbsDirective);

var _ParenchymController = require('./ParenchymController');

var _ParenchymController2 = _interopRequireDefault(_ParenchymController);

var _filter = require('./filter');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function config() {}
config.$inject = [];

function run() {}
run.$inject = [];

var _module = _angular2.default.module('pym', []).config(config).run(run).service('pym.stickyBreadcrumbsService', _StickyBreadcrumbsService2.default.serviceFactory).service('pym.recursionHelper', _RecursionHelper2.default.serviceFactory).controller('pym.controller', _ParenchymController2.default).directive('pymStickyBreadcrumbs', _StickyBreadcrumbsDirective2.default.directiveFactory).filter('trusted', _filter.trustedFilter);

exports.default = _module;
//# sourceMappingURL=ParenchymModule.js.map