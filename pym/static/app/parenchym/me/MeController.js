'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

var _angular = require('angular');

var _angular2 = _interopRequireDefault(_angular);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var MeController = function () {
    function MeController(meService, growlerService) {
        _classCallCheck(this, MeController);

        this.meService = meService;
        this.growlerService = growlerService;

        this.ToolsMenu = {
            isDisabled: false,
            isOpen: false
        };
    }

    _createClass(MeController, [{
        key: 'doThis',
        value: function doThis() {
            this.growlerService.info('Done this');
        }
    }]);

    return MeController;
}();

MeController.$inject = ['pym.me.service', 'pym.growler.service'];

exports.default = MeController;
//# sourceMappingURL=MeController.js.map
