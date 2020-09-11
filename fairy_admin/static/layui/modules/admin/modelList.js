
layui.define(["jquery", "laytpl", "table", "soulTable", "layer", "upload", "form", "dashboard"], function(exports) {
    var laytpl = layui.laytpl
    , table = layui.table
    , soulTable = layui.soulTable
    , $ = layui.$
    , layer = layui.layer
    , form = layui.form
    , dashboard = layui.dashboard;

    function ajaxAction(url, action, ids, tableFilter, index=null) {
        $.ajax({
            async: true,
            method: "POST",
            url: url,
            // contentType: "application/json",
            data: {
                "_data": JSON.stringify({ids: ids})
            },
            success: function(result) {
                if (result.code === 0) {
                    if (index) {
                        layer.close(index);
                    }
                    table.reload(tableFilter);
                } else {
                    layer.alert(result.msg);
                }
            }
        });
    }

    function showConfirmation(url, action, confirmation, ids, tableFilter) {
        layer.confirm(confirmation, function(index) {
            ajaxAction(url, action, ids, tableFilter, index);
        });
    }

    function addParameterToURL(_url, key, value){
        _url += (_url.split('?')[1] ? '&':'?') + key + '=' + value;
        return _url;
    }

    function processAction(action, ids, tableId) {
        if (action) {
            var actionData = action.data;
            var event = action.event;
            if (action.ajax) {
                if (actionData.confirmation) {
                    showConfirmation(actionData.url, event, actionData.confirmation, ids, tableId);
                } else {
                    ajaxAction(actionData.url, event, ids, tableId);
                }
            } else if (actionData.modal) {
                var url = actionData.url;
                if (ids.length > 0) {
                    url = addParameterToURL(actionData.url, 'id', ids[0]);
                }
                var callback = function(tableId) {
                    table.reload(tableId);
                };
                var requestParams = {
                    method: "POST",
                    url: url,
                    processData: false,
                    data: JSON.stringify({
                        "ids": ids
                    }),
                    contentType: "application/json"
                };
                dashboard.showAjaxModal(requestParams, tableId, actionData.title, actionData.form, actionData.btn, callback);
            } else {
                var url = actionData.url;
                if (ids.length > 0) {
                    url = addParameterToURL(actionData.url, 'id', ids[0]);
                }
                window.location.href = url;
            }
        }
    }

    function renderTable(_id, elem, toolbar, config, cols, height=null) {
        function optionName(key) {
            var value = key[this.field];
            for (var idx in this.options) {
                var option = this.options[idx];
                if (option[0] === key[this.field][0]) {
                    return option[1];
                }
            }
            return value;
        }
        for (var idx in cols) {
            var col = cols[idx];
            if (col.options !== undefined) {
                col.templet = optionName.bind(col);
            }
        }
        var tableOptions = {
            elem: elem,
            toolbar: toolbar,
            defaultToolBar: config.default_tool_bar,
            url: config.url,
            page: config.page,
            cols: [cols],
            soulSort: false,
            height: height,
            filter: {
                items: ["data", "condition", "editCondition"]
            },
            done: function() {
                soulTable.render(this);
                // 修复由 soulTable 导致的表格高度问题
                var filterHeight = $("[lay-id=\"" + _id + "\"]").find(".soul-bottom-contion").outerHeight();
                if (filterHeight) {
                    var targetHeight = $("[lay-id=\"" + _id + "\"]").find(".layui-table-body").outerHeight() + filterHeight;
                    $("[lay-id=\"" + _id + "\"]").find(".layui-table-body").css("height", targetHeight);
                }

                // TODO check language, english only
                var total = $("[lay-id=\"" + _id + "\"] .layui-laypage-count").text();
                if (!total) {
                    return;
                }
                total = /共 (\d+) 条/.exec(total)[1];
                $("[lay-id=\"" + _id + "\"] .layui-laypage-skip").contents().filter(function() {
                    return this.nodeType == Node.TEXT_NODE;
                }).each(function(idx, item) {
                    if (item.nodeValue === "到第") {
                        item.nodeValue = "Page";
                    } else if (item.nodeValue === "页") {
                        item.nodeValue = "";
                    }
                });
                $("[lay-id=\"" + _id + "\"] .layui-laypage-btn").text("Go");
                $("[lay-id=\"" + _id + "\"] .layui-laypage-btn").css("marginLeft", "0");
                $("[lay-id=\"" + _id + "\"] .layui-laypage-count").text(total + " in Total");
                $("[lay-id=\"" + _id + "\"] .layui-laypage-limits select option").each(function(idx, item) {
                    var text = $(item).text();
                    var num = /(\d+) 条\/页/.exec(text)[1];
                    $(item).text(num + " / Page");
                });
            }
        }
        table.render(tableOptions);
    }

    var modelList = {
        configs: {},
        render: function(options) {
            var elem = options.elem;
            var _id = $(elem).attr("id");
            $.ajax({
                method: "GET",
                url: options.configUrl,
                success: function(result) {
                    modelList.configs[_id] = result;
                    var cols = [];
                    if (result.column_display_numbers) {
                        cols.push({
                            type: "numbers"
                        });
                    }
                    if (result.column_display_checkbox || options.checkbox ) {
                        cols.push({
                            type: "checkbox"
                        });
                    }
                    cols = cols.concat(result.cols);
                    if (result.column_display_actions) {
                        cols.push({
                            minWidth: result.column_actions_width || 178,
                            align: "center",
                            // fixed: "right",
                            toolbar: options.rowToolbar
                        });
                    }
                    if (options.toolbar && options.toolbar !== 'default' && options.toolbar !== true) {
                        var toolbarTpl = $(options.toolbar).html();
                        laytpl(toolbarTpl).render(result, function(html) {
                            renderTable(_id, elem, html, result, cols, options.height || null);
                        });
                    } else {
                        renderTable(_id, elem, options.toolbar || false, result, cols, options.height || null);
                    }
                    table.on("sort(" + _id + ")", function(obj) {
                        table.reload(_id, {
                            where: {
                                field: obj.field,
                                order: obj.type
                            }
                        });
                    });
                    table.on("tool(" + _id + ")", function(obj) {
                        var {event, data} = obj;
                        var action;
                        for (var index in data._actions) {
                            var _action = data._actions[index];
                            if (_action.event === event) {
                                action = _action;
                                break;
                            }
                        }
                        processAction(action, [data._id], _id);
                    });
                    table.on("toolbar(" + _id + ")", function(obj) {
                        var {event, config} = obj;
                        if (event === 'reload') {
                            table.reload(_id);
                            return;
                        }
                        var checkStatus = table.checkStatus(config.id);
                        var ids = [];
                        for (var index in checkStatus.data) {
                            var item = checkStatus.data[index];
                            ids.push(item._id);
                        }
                        var modelConfig = modelList.configs[config.id];
                        var action;
                        for (var index in modelConfig.actions) {
                            var _action = modelConfig.actions[index];
                            if (_action.event === event) {
                                action = _action;
                                break;
                            }
                        }
                        processAction(action, ids, config.id);
                    });
                },
                error: function(e) {
                    layer.msg("Can not load list config");
                }
            });
        }
    };

    exports("modelList", modelList);
});
