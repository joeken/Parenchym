var FsController = PymApp.controller('FsController',
        ['$scope', '$http', '$q', '$window', '$upload', 'RC', 'T', 'PymApp.GridTools', 'uiGridConstants', '$timeout', '$log', '$modal',
function ($scope,   $http,   $q,   $window,   $upload,   RC,   T,   GridTools,          uiGridConstants,   $timeout,   $log,   $modal) {

    "use strict";
    

    var ctrl = this;


    var FsService = {
        createDirectory: function (path, dirName) {
            var httpConfig = {},
                postData = {
                    name: dirName,
                    path: this.pathToStr(path)
                };
            return $http.post(RC.urls.create_directory, postData, httpConfig)
            .then(function (resp) {
                if (resp.data.ok) {
                    // Noop
                }
                PYM.growl_ajax_resp(resp.data);
                return resp;
            }, function (result) {
                return result;
            });
        },

        deleteItems: function (path, names, reason) {
            var httpConfig = {
                params: {
                    path: this.pathToStr(path),
                    names: names,
                    reason: reason
                }
            };
            return $http.delete(RC.urls.delete_items, httpConfig)
            .then(function (resp) {
                if (resp.data.ok) {
                    // NOOP
                }
                PYM.growl_ajax_resp(resp.data);
                return resp;
            }, function (result) {
                return result;
            });
        },

        undeleteItems: function (path, names) {
            var httpConfig = {},
                putData = {
                    path: this.pathToStr(path),
                    names: names
                };
            return $http.put(RC.urls.undelete_items, putData, httpConfig)
            .then(function (resp) {
                if (resp.data.ok) {
                    // NOOP
                }
                PYM.growl_ajax_resp(resp.data);
                return resp;
            }, function (result) {
                return result;
            });
        },

        loadItems: function (path, includeDeleted) {
            $log.log('got oath', path);
            var httpConfig = {params: {
                path: this.pathToStr(path),
                incdel: includeDeleted
            }};
            return $http.get(RC.urls.load_items, httpConfig)
            .then(function (resp) {
                if (resp.data.ok) {
                    // noop
                }
                else {
                    PYM.growl_ajax_resp(resp.data);
                }
                return resp;
            }, function (result) {
                return result;
            });
        },

        loadTree: function (rootPath, filter, includeDeleted) {
            var httpConfig = {params: {
                path: rootPath,
                filter: filter,
                incdel: includeDeleted
            }};
            return $http.get(RC.urls.load_tree, httpConfig)
            .then(
                function (resp) {
                    if (resp.data.ok) {
                        // noop
                    }
                    else {
                        PYM.growl_ajax_resp(resp.data);
                    }
                    return resp;
                },
                function (result) {
                    return result;
                }
            );
        },

        loadFsProperties: function () {
            var httpConfig = {params: {}};
            return $http.get(RC.urls.load_fs_properties, httpConfig)
            .then(
                function (resp) {
                    if (resp.data.ok) {
                        return resp;
                    }
                    else {
                        PYM.growl_ajax_resp(resp.data);
                        return false;
                    }
                },
                function (result) {
                    return result;
                }
            );
        },

        loadItemProperties: function (path, name) {
            var httpConfig = {params: {
                path: this.pathToStr(path),
                name: name
            }};
            return $http.get(RC.urls.load_item_properties, httpConfig)
            .then(
                function (resp) {
                    if (resp.data.ok) {
                        return resp;
                    }
                    else {
                        PYM.growl_ajax_resp(resp.data);
                        return false;
                    }
                },
                function (result) {
                    return result;
                }
            );
        },

        buildDownloadUrl: function (path, name) {
            var pp, s;
            // Make local copy of original path
            pp = path.slice();
            // Remove filesystem root, because browser is already there:
            // http://HOST:PORT/TENANT/fs/@@_br_
            if (pp[0].name === 'fs') { pp.shift(); }
            // Stringify path and append name
            s = pp.length ? this.pathToStr(pp) + '/' + name : name;
            // Get current url and apply our path string
            return $window.location.href.replace(/@@_br_/, s);
        },

        pathToStr: function (path) {
            var pp = [];
            angular.forEach(path, function (x) {
                pp.push(x.name);
            });
            return pp.join('/');
        }
    };

    ctrl.canUpload = true;
    ctrl.canDownload = false;
    ctrl.canDeleteItems = false;
    ctrl.canUndeleteItems = false;
    ctrl.canOpenNode = false;

    ctrl.GlobalOptions = {
        minSize: RC.min_size,
        maxSize: RC.max_size,
        allow: RC.allow,
        deny: RC.deny,

        includeDeleted: false,
        overwrite: false
    };


    ctrl.toggleIncludeDeleted = function () {
        this.GlobalOptions.includeDelete = !this.GlobalOptions.includeDelete;
        ctrl.FileTree.includeDeleted = this.GlobalOptions.includeDelete;
        ctrl.FileBrowser.includeDeleted = this.GlobalOptions.includeDelete;
        ctrl.FileTree.refresh();
        ctrl.FileBrowser.refresh();
    };


    ctrl.createDirectory = function () {
        var path = ctrl.FileTree.path,
            dirName = $window.prompt(T.prompt_dir_name);
        if (! dirName ) {return;}
        FsService.createDirectory(path, dirName)
        .then(
            function () {
                ctrl.FileTree.refresh();
                ctrl.FileBrowser.refresh();
            });
    };


    ctrl.deleteItems = function () {
        var path = ctrl.FileTree.path,
            names = [],
            reason = $window.prompt(T.prompt_delete_items);
        if (! reason) { return; }
        // Collect selected rows
        angular.forEach(ctrl.FileBrowser.api.selection.getSelectedRows(), function (r) {
            names.push(r._name);
        });
        if (! names ) {return;}
        FsService.deleteItems(path, names, reason)
        .then(
            function () {
                ctrl.FileTree.refresh();
                ctrl.FileBrowser.refresh();
            });
    };


    ctrl.undeleteItems = function () {
        var path = ctrl.FileTree.path,
            names = [];
        if (! $window.confirm(T.confirm_undelete_items)) { return; }
        // Collect selected rows
        angular.forEach(ctrl.FileBrowser.api.selection.getSelectedRows(), function (r) {
            names.push(r._name);
        });
        if (! names ) {return;}
        FsService.undeleteItems(path, names)
        .then(
            function () {
                ctrl.FileTree.refresh();
                ctrl.FileBrowser.refresh();
            });
    };


    ctrl.openNode = function () {
        var sel = ctrl.FileBrowser.api.selection.getSelectedRows();
        if (! sel.length) { return; }
        ctrl.FileTree.setPathById(sel[0].id);
    };


    ctrl.openFsPropertiesDlg = function () {
        var modalInstance = $modal.open({
            templateUrl: 'FsPropertiesDlgTpl.html',
            controller: 'FsPropertiesDlgController as dlg',
            size: null, // 'sm', 'lg'
            resolve: {
                loadResp: function () { return FsService.loadFsProperties(); }
            }
        });
        modalInstance.result
        .then(function (data) {
                $log.info('Data to save: ', data);
            }, function () {
                $log.info('Modal dismissed at: ' + new Date());
            }
        );
    };


    ctrl.openItemPropertiesDlg = function () {
        var path = ctrl.FileTree.path;
        var name = ctrl.FileBrowser.api.selection.getSelectedRows()[0]._name;
        var modalInstance = $modal.open({
            templateUrl: 'ItemPropertiesDlgTpl.html',
            controller: 'ItemPropertiesDlgController as dlg',
            size: 'lg', // 'sm', 'lg'
            resolve: {
                loadResp: function () { return FsService.loadItemProperties(path, name); },
                path: function () { return FsService.pathToStr(path); }
            }
        });
        modalInstance.result
        .then(function (data) {
                $log.info('Data to save: ', data);
            }, function () {
                $log.info('Modal dismissed at: ' + new Date());
            }
        );
    };



    /*
     * Tools menu
     */
    ctrl.ToolsMenu = {
        isOpen: false,
        isDisabled: false,

        deleteItems: function () {
            ctrl.deleteItems();
            this.isOpen = false;
        },

        undeleteItems: function () {
            ctrl.undeleteItems();
            this.isOpen = false;
        },

        createDirectory: function () {
            ctrl.createDirectory();
            this.isOpen = false;
        },

        openNode: function () {
            ctrl.openNode();
            this.isOpen = false;
        },

        openFsPropertiesDlg: function () {
            ctrl.openFsPropertiesDlg();
            this.isOpen = false;
        },

        openItemPropertiesDlg: function () {
            ctrl.openItemPropertiesDlg();
            this.isOpen = false;
        }
    };


    ctrl.cbOnRowSelectionChanged = function (row) {
        var sel = ctrl.FileBrowser.api.selection.getSelectedRows();
        if (sel.length) {
            if (sel[0].mime_type.match(/.*inode.*/)) {
                ctrl.canDownload = false;
            }
            else {
                ctrl.canDownload = true;
                ctrl.downloadUrl = FsService.buildDownloadUrl(ctrl.FileTree.path, sel[0]._name);
            }
            ctrl.canDeleteItems = true;
            ctrl.canUndeleteItems = true;
            ctrl.canOpenNode = true;
            ctrl.canOpenItemPropertiesDlg = true;
        }
        else {
            ctrl.canDownload = false;
            ctrl.canDeleteItems = false;
            ctrl.canUndeleteItems = false;
            ctrl.canOpenNode = false;
            ctrl.canOpenItemPropertiesDlg = false;
        }
    };


    ctrl.FileBrowser = {
        rc: {},
        path: [],
        includeDeleted: false,
        files: [],
        rejectedFiles: [],
        data: [],
        api: null,

        cbWindowResized: function (ghostPosition, length) {
            if (this.api) {
                $timeout(this.api.core.handleWindowResize, 100);
            }
        },
        windowResized: null,

        setPath: function (path) {
            this.path = path;
            this.loadItems(path);
        },

        postProcessItems: function (items) {
            angular.forEach(items, function (it) {
                it.ctime = it.ctime ?  new Date(it.ctime) : null;
                it.mtime = it.mtime ? new Date(it.mtime) : null;
                it.dtime = it.dtime ? new Date(it.dtime) : null;
                it.owner2 = function () { return this.owner ? this.owner + ' (' + this.owner_id + ')' : '' };
                it.editor2 = function () { return this.editor ? this.editor + ' (' + this.editor_id + ')' : '' };
                it.deleter2 = function () { return this.deleter ? this.deleter + ' (' + this.editor_id + ')' : '' };
            });
        },

        loadItems: function (path) {
            var self = this;
            self.pym.loading = true;
            FsService.loadItems(path, self.includeDeleted)
            .then(function (resp) {
                self.pym.loading = false;
                if (resp.data.ok) {
                    self.postProcessItems(resp.data.data.rows);
                    self.options.data = resp.data.data.rows;
                }
            }, function (result) {
                self.pym.loading = false;
            });
        },

        refresh: function () {
            this.loadItems(this.path);
        },

        saveRow: function () {
            // TODO
        },

        cbOnRegisterApi: function (gridApi) {
            var self = this;
            self.api = gridApi;
            $timeout(gridApi.core.handleWindowResize, 100);
            gridApi.edit.on.afterCellEdit($scope, function(rowEntity, colDef, newValue, oldValue) {
                $log.log('edited row id:' + rowEntity.id + ' Column:' + colDef.name + ' newValue:' + newValue + ' oldValue:' + oldValue);
            });
            gridApi.rowEdit.on.saveRow($scope, ctrl.FileBrowser.saveRow);

            gridApi.selection.on.rowSelectionChanged($scope, function (row) {
                self.rc.onRowSelectionChanged(row);
            });
        },

        init: function (rc) {
            this.rc = rc;
            this.options.onRegisterApi = angular.bind(this, this.cbOnRegisterApi);
            this.indexColumnDefs();
            // Just load the items, our path is set by the FileTree
            this.loadItems(rc.rootPath);
            this.windowResized = angular.bind(this, this.cbWindowResized);
        },

        /**
         * Checks given mime-type against pattern from ``allow`` and ``deny``
         * and returns true if mime-type is allowed, false otherwise.
         */
        checkType: function (ty) {
            var self = this,
                i, imax, pat, good;
            if (! ty) {ty = 'application/octet-stream';}
            ty = ty.split('/');
            $log.log(ty);
            // Is given mime type allowed?
            good = false;
            for (i=0, imax=self.allow.length; i<imax; i++) {
                pat = self.allow[i];
                if (pat.search(/\*/) > -1 && pat.search(/\.\*/) === -1) {
                    pat = pat.replace(
                        /\*/g,
                        '.*'
                    );
                }
                pat = pat.split('/');
                if (ty[0].search(pat[0]) > -1 && ty[1].search(pat[1]) > -1) {
                    good = true;
                    break;
                }
            }
            if (! good) {return false;}
            // Is given mime type denied?
            for (i=0, imax=self.deny.length; i<imax; i++) {
                pat = self.deny[i];
                if (pat.search(/\*/) > -1 && pat.search(/\.\*/) === -1) {
                    pat = pat.replace(
                        /\*/g,
                        '.*'
                    );
                }
                pat = pat.split('/');
                if (ty[0].search(pat[0]) > -1 || ty[1].search(pat[1]) > -1) {
                    good = false;
                    break;
                }
            }
            return good;
        },
        checkSize: function (sz) {
            return (sz >= this.minSize && sz <= this.maxSize);
        },
        uploader: null,
        upload: function () {
            var self = this,
                i, imax, f,
                allowedFiles = [], deniedFiles = [];
            for (i=0, imax=self.files.length; i<imax; i++) {
                f = self.files[i];
                if (! self.checkType(f.type)) {
                    deniedFiles.push([f, '${_("File type not allowed")}']);
                    continue;
                }
                if (! self.checkSize(f.size)) {
                    deniedFiles.push([f, '${_("File too large")}']);
                    continue;
                }
                allowedFiles.push(f);
            }
            if (deniedFiles.length) {
                var m = [];
                for (i=0, imax=deniedFiles.length; i<imax; i++) {
                    m.push('<p>' + deniedFiles[i][0].name + ': ' + deniedFiles[i][1] + '</p>');
                }
                PYM.growl({kind: 'warn', text: m.join('')});
            }
            if (allowedFiles.length) {
                self.uploader = $upload.upload({
                    url: RC.urls.upload, // upload.php script, node.js route, or servlet url
                    //method: 'POST' or 'PUT',
                    //headers: {'Authorization': 'xxx'}, // only for html5
                    //withCredentials: true,
                    data: {
                        path: self.rc.tree.pathToStr(),
                        overwrite: self.overwrite
                    },
                    file: allowedFiles // single file or a list of files. list is only for html5
                    //fileName: 'doc.jpg' or ['1.jpg', '2.jpg', ...] // to modify the name of the file(s)
                    //fileFormDataName: myFile, // file formData name ('Content-Disposition'), server side request form name
                    // could be a list of names for multiple files (html5). Default is 'file'
                    //formDataAppender: function(formData, key, val){}  // customize how data is added to the formData.
                    // See #40#issuecomment-28612000 for sample code

                }).progress(function (evt) {
                    $log.log('progress: ' + parseInt(100.0 * evt.loaded / evt.total) + '% file :', evt.config.file);
                }).success(function (data, status, headers, config) {
                    // file is uploaded successfully
                    $log.log('file ', config.file, ' is uploaded successfully. Response: ', data);
                    PYM.growl_ajax_resp(data);
                    if (data.ok) {
                        // TODO
                    }
                    self.ls();
                });
                //.error(...)
                //.then(success, error, progress); // returns a promise that does NOT have progress/abort/xhr functions
                //.xhr(function(xhr){xhr.upload.addEventListener(...)}) // access or attach event listeners to
                //the underlying XMLHttpRequest
            }
        }
    };

    var nodeIdTpl = '<div class="ui-grid-cell-contents"><span tooltip-trigger="click" tooltip-append-to-body="true" tooltip-html-unsafe="{{row.entity.id}}">{{row.entity.id}}</span></div>';
    var aggNumTpl = '<div class="ui-grid-cell-contents" style="text-align: right;">{{grid.getColumn("size").getAggregationValue()|number:0}}</div>';

    ctrl.FileBrowser.options = {
        data: ctrl.FileBrowser.data,

        enableSorting: true,
        useExternalSorting: false,

        enableFiltering: false,
        useExternalFiltering: false,

        enableColumnMenus: false,

        enableRowSelection: true,
        //enableSelectAll: true,
        //multiSelect: true,
        noUnselect: false,

        enableCellEditOnFocus: false,

        showGridFooter: true,
        enableFooterTotalSelected: true,
        selectionRowHeaderWidth: '30',

        showColumnFooter: true,

        columnDefs: [
            { name:'id', displayName: 'ID', enableFiltering: false, enableCellEdit: false, width: 50, cellTemplate:nodeIdTpl },
            { name:'_name', displayName: 'Name', enableCellEdit: true, width: 230 },
            { name:'_title', displayName: 'Title', enableCellEdit: true, width: 230 },
            { name:'rev', displayName: 'Rev', enableCellEdit: false, width: 45, cellFilter: "number:0", cellClass: "text-right" },
            { name:'size', displayName: 'Size', enableCellEdit: false, width: 80, cellFilter: "number:0", cellClass: "text-right", aggregationType: uiGridConstants.aggregationTypes.sum, aggregationHideLabel: true, footerCellTemplate: aggNumTpl },
            { name:'nchildren', displayName: 'Children', enableCellEdit: false, width: 80, cellFilter: "number:0", cellClass: "text-right" },
            { name:'mime_type', displayName: 'Mime-Type', enableCellEdit: false, width: 150 },
            { name:'ctime', displayName: 'CTime', cellFilter: 'date: "yyyy-MM-dd HH:mm"', enableCellEdit: false, width: 150 },
            { name:'owner', field: 'owner2()', displayName: 'Owner', enableCellEdit: false, width: 150 },
            { name:'mtime', displayName: 'MTime', cellFilter: 'date: "yyyy-MM-dd HH:mm"', enableCellEdit: false, width: 150 },
            { name:'editor', field: 'editor2()', displayName: 'Editor', enableCellEdit: false, width: 150 },
            { name:'dtime', displayName: 'DTime', cellFilter: 'date: "yyyy-MM-dd HH:mm"', enableCellEdit: false, width: 150 },
            { name:'deleter', field: 'deleter2()', displayName: 'Deleter', enableCellEdit: false, width: 150 },
            { name:'deletion_reason', displayName: 'Reason', enableCellEdit: false, width: 150 }
        ]
    };


    ctrl.FileTree = {
        rc: {},
        includeDeleted: false,
        data: [],
        dataById: {},
        /**
         * Current path as list of nodes from root to current node.
         * DO NOT set this directly
         */
        path: [],
        selected: null,
        toolsIsOpen: false,
        toolsIsDisabled: false,
        filter: 'dirs',
        loading: false,
        rootNodesScope: null,

        callbacks: {},
        cbAccept: function (sourceNodeScope, destNodeScope, destIndex) {
            $log.log('on accept', sourceNodeScope, destNodeScope, destIndex);
            if (destNodeScope.nodrop || destNodeScope.outOfDepth(sourceNodeScope) || destNodeScope.isParent(sourceNodeScope)) {
                return false;
            }
            return true;
        },
        cbSelect: function(node) {
            var mv = node.$modelValue;
            this.setPathById(mv.id);
        },

        /**
         * Initialises the file tree.
         *
         * Expected properties of ``rc`` are:
         *
         * - rootPath {string} - Path as string that points to the filesystem
         *       root.
         * - browser {object} - Object of the file browser component.
         * - globalOptions {object} - Object with global settings.
         *
         * @param {object } rc - Object with configuration
         */
        init: function (rc) {
            var self = this;
            this.rc = rc;
            this.callbacks.accept = angular.bind(this, this.cbAccept);
            this.callbacks.select = angular.bind(this, this.cbSelect);
            this.loadItems(rc.rootPath, this.data).then(
                function () {
                    // This is the only case where we set path directly
                    self.path = [self.data[0]];
                    self.rc.browser.path = self.path;
                }
            );
        },

        /**
         * Processes items after loading before applying.
         *
         * Stuffs parent to reach node, so we can build the path more easily.
         * Also indexes by ID (property ``dataById``).
         *
         * @param {list} items.
         */
        postProcessItems: function (items) {
            var self = this;
            // Stuff parent to each node, so we can build the path more easily.
            // Also index by ID.
            function index(dd, parent) {
                var i, imax;
                for (i=0, imax=dd.length; i<imax; i++) {
                    self.dataById[dd[i].id] = dd[i];
                    dd[i].parent = parent;
                    if (dd[i].nodes) {index(dd[i].nodes, dd[i]);}
                }
            }
            index(items, null);
        },

        /**
         * Load the FS tree starting at given path.
         *
         * Data structure must be a nested list. Each list item represents a
         * node with properties ``id``, ``name``, ``title``, and ``sortix``.
         * (Property ``parent`` is applied by postprocessing.) Property
         * ``nodes`` is a list with child nodes:
         *
         *     [
         *         {id: 1, name: 'foo', title: 'Foo', sortix: 5000, nodes: [
         *             {id: 2, name: 'bar', title: 'Bar', sortix: 5000, nodes: [
         *                 ...
         *             ]}
         *         ]}
         *     ]
         *
         * HTML template of the tree nodes must match this structure.
         *
         * Sets property ``loading`` to true during loading. Use this flag e.g.
         * if you want to display a loading indicator.
         *
         * @param {string} rootPath - Start path as string.
         * @param {array} dst - Pushes loaded children onto this list.
         */
        loadItems: function (rootPath, dst) {
            var self = this;
            self.loading = true;
            return FsService.loadTree(rootPath, self.filter, self.includeDeleted)
            .then(
                function (resp) {
                    var j, jmax;
                    self.loading = false;
                    if (resp.data.ok) {
                        self.postProcessItems(resp.data.data);
                        for (j=0, jmax=resp.data.data.length; j<jmax; j++) {
                            dst.push(resp.data.data[j]);
                        }
                    }
                },
                function (result) {
                    self.loading = false;
                }
            );
        },

        /**
         * Reloads tree data from server
         */
        refresh: function () {
            var foo = [];
            this.loadItems(this.rc.rootPath, foo)
            .then(
                $timeout(angular.bind(this, this.expandPath), 1000)
            );
            this.data = foo;
        },

        /**
         * Changes current path to path to node with given ID.
         *
         * @param {int} id - ID of node
         */
        setPathById: function (id) {
            var self = this;
            var dst = self.dataById[id], root = dst, pp = [root];
            while (root.parent) {
                root = root.parent;
                pp.unshift(root);
            }
            self.setPath(pp);
        },

        /**
         * Sets the path and performs actions needed for the change.
         *
         * Calls ``onPathChanged`` if that is defined.
         *
         * @param {list} pp - New path as list of nodes.
         */
        setPath: function (pp) {
            this.path = pp;
            this.selected = this.path[this.path.length-1];
            this.rc.browser.setPath(pp);
            this.expandPath();
            if (this.onPathChanged) {this.onPathChanged();}
        },

        expandPath: function () {
            var i, imax, p,
                scope = this.getRootNodesScope(), prevScope = null,
                cnn, j, jmax;
            $log.log('current root nodes scope', scope);
            // Loop from first node down to last node that is not leaf
            // (no need -- or avail -- to expand the leaf)
            for (i=0, imax=this.path.length-1; i<imax; i++) {
                p = this.path[i];
                $log.log('Trying to expand path segment', p.name);

                if (i < imax) {
                    cnn = scope.childNodes();
                    // Memorize scope as long as it is known
                    if (scope) {prevScope = scope;}
                    scope = null;
                    for (j=0, jmax=cnn.length; j<jmax; j++) {
                        if (cnn[j].$modelValue.name === p.name) {
                            scope = cnn[j];
                            break;
                        }
                    }
                }
                if (! scope) {
                    $log.warn('No scope found for path segment', p.name);
                }
                else {
                    $log.log('expanding node', scope.node.name);
                    scope.expand();
                }
            }
            /*
            // Now ensure that the leaf node is visible
            p = this.path[this.path.length - 1];
            // Fallback to last known scope
            if (! scope) {scope = prevScope;}
            // From here, fetch the scope of the path's leaf node
            cnn = scope.childNodes();
            for (i=0, imax=cnn.length; i<imax; i++) {
                if (cnn[i].$modelValue.name === p.name) {
                    scope = cnn[i];
                    break;
                }
            }
            $log.log('path leaf node', scope);
            // Hmm, nice idea, but this scrolls the whole window, not just the tree...
            scope.$element[0].scrollIntoView({block: "start", behavior: "smooth"});
            */
        },

        onPathChanged: null,

        /**
         * Returns scope of the tree's first nodes element, i.e. the nodes container.
         *
         * @returns {*} - Scope of first nodes container.
         */
        getRootNodesScope: function() {
            // Getting element's scope with .scope() needs debug data to be enabled!
            var treeScope = angular.element(document.getElementById("fileTreeRootNodes")).isolateScope(),
                rootNodesScope;
            if (! treeScope) {return null;}
            rootNodesScope = treeScope.$nodesScope;
            return rootNodesScope;
        },

        toggle: function (scope) {
            scope.toggle();
        },

        toggleSelected: function (scope) {
            $log.log('toggle selected', scope);
            scope.toggleSelected();
        },

        collapseAll: function () {
            $scope.$broadcast('collapseAll');
        },

        expandAll: function () {
            $scope.$broadcast('expandAll');
        }
    };


    function init() {
        GridTools.enhance(ctrl.FileBrowser);
        ctrl.FileBrowser.init({
            tree: ctrl.FileTree,
            globalOptions: ctrl.GlobalOptions,
            rootPath: RC.path,
            onRowSelectionChanged: angular.bind(ctrl, ctrl.cbOnRowSelectionChanged)
        });
        ctrl.FileTree.init({
            browser: ctrl.FileBrowser,
            globalOptions: ctrl.GlobalOptions,
            rootPath: RC.path
        });
    }


    /*
     * Run immediately
     */
    init();
}]);
