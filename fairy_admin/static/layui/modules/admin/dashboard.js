layui.define(["jquery", "layer", "form", "layedit", "element", "laydate", "upload"], function(exports) {
    var layer = layui.layer
    , $ = layui.$
    , form = layui.form
    , layedit = layui.layedit
    , element = layui.element
    , laydate = layui.laydate
    , upload = layui.upload;

    var dashboard = {
        showAjaxModal: function(filter, url, title, isEdit, btn, callback=null) {
            var btn;
            $.ajax({
                async: true,
                method: "GET",
                url: url,
                success: function(result) {
                    var index = layer.open({
                        type: 1,
                        zIndex: 1099,   // 避免与 ckeditor 上传组件的 zIndex 冲突
                        area: "640px",
                        title: title,
                        content: result,
                        btn: btn,
                        success: function(layero, index) {
                            var contentRoot = $(layero).find(".layui-layer-content").children()[0];
                            if (contentRoot) {
                                $(contentRoot).data("layer-index", index);
                            }
                            var form = $(layero).find("form");
                            if (form) {
                                $(form).data("layer-index", index);
                                var btn = $(layero).find("[lay-submit]");
                                if (btn.size() === 0) {
                                    $(form).append("<button type=\"submit\" style=\"display: none;\" lay-submit lay-filter=\"" + filter + "-modal-form\">submit</button>");
                                    btn = $(layero).find("[lay-submit]");
                                }
                            }
                        },
                        yes: function(index, layero) {
                            var btn = $(layero).find("[lay-submit]");
                            if (btn) {
                                btn.click();
                            } else {
                                layer.close(index);
                            }
                        }
                    });
                    if (isEdit) {
                        dashboard.refreshForm();
                    }
                }
            });
            form.on("submit(" + filter + "-modal-form)", function(data) {
                if (!data.form) {
                    return false;
                }
                var index = $(data.form).data("layer-index");
                $(data.form).find("textarea").each(function(idx, item) {
                    var editorId = $(item).data("layedit-id");
                    if (editorId !== null && editorId !== undefined) {
                        layedit.sync(editorId);
                    }
                });
                const formData = new FormData(data.form);
                $.ajax({
                  method: $(data.form).attr("method"),
                  url: $(data.form).attr("action"),
                  data: formData,
                  processData: false,
                  contentType: false,
                  success: function(result) {
                    if (result.code === 0) {
                      callback && callback(filter);
                      layer.close(index);
                    } else {
                      if (result.errors) {
                        for (var f in result.errors) {
                          var field = result.errors[f];
                          layer.alert(field.label + ": " + field.errors[0], {
                            "title": result.msg
                          });
                          break;
                        }
                      } else {
                        layer.alert(result.msg);
                      }
                    }
                  }
                });
                return false;
            });
        },
        listen: function() {
            $("body").on("click", "[data-side-fold]", function() {
                var fold = $(this).data("side-fold");
                if (fold == "0") {
                    $(this).data("side-fold", "1");
                    $(this).removeClass("layui-icon-shrink-right");
                    $(this).addClass("layui-icon-spread-left");
                    $("body").addClass("layout-side-fold");
                } else {
                    $(this).data("side-fold", "0");
                    $(this).removeClass("layui-icon-spread-left");
                    $(this).addClass("layui-icon-shrink-right");
                    $("body").removeClass("layout-side-fold");
               }
            });
            $(".btn-modal-action").on("click", function() {
                var filter = "form";
                var url = $(this).data("url");
                var title = $(this).data("title");
                var isEdit = $(this).data("form");
                var btn = $(this).data("btn");
                var callback = $(this).data("callback");
                dashboard.showAjaxModal(filter, url, title, isEdit, btn, function(id) {
                    eval(callback);
                });
                console.log(dashboard);
                console.log(isEdit, title, url);
            });
        },
        refreshForm: function() {
            form.render();
            $(".xm-select").each(function(i, e) {
                var name = $(e).data("name");
                var options = $(e).data("options");
                xmSelect.render({
                    el: e,
                    name: name,
                    data: options,
                    template({ item, sels, name, value }){
                        // Bugfix to xm-select, when name has patter <*>, it can not be displaed normally
                        return $('<div/>').text(name).html();
                    },
                });
            });
            $("input.laydate").each(function(i, e) {
                var type = $(e).data("type");
                laydate.render({
                    elem: e,
                    type: type
                });
            });
            $("button.btn-upload-file").each(function(i, e) {
                var show = null;
                upload.render({
                    elem: e,
                    url: $(e).data("upload-url"),
                    accept: $(e).data("accept"),
                    before: function() {
                        show = layer.open({
                            type: 1,
                            title: "{{ _gettext('Upload') }}",
                            content: '<div style="margin: 10px 20px; width: 220px; "><div class="layui-progress layui-progress-big" lay-showpercent="true" lay-filter="uploadfile"><div class="layui-progress-bar" lay-percent="" id="uploadfile"></div></div><p><span id="uploadfilemsg">Uploading</span></p></div>',
                            end: function () {
                                element.progress("uploadfile", "0%");
                            }
                        });
                    },
                    progress: function(n, elem){
                        var percent = n + "%" //获取进度百分比
                        element.progress("uploadfile", percent); //可配合 layui 进度条元素使用
                    },
                    done: function(res) {
                        layer.close(show);
                        if (res.code !== 0) {
                            layer.alert(res.msg);
                        }
                        var data = res.data;
                        var name = $(e).attr("name");
                        name = "_" + name + "-changed";
                        if ($(e).parent().find("[name=\"" + name + "\"]").size() === 0) {
                            $(e).parent().append("<input type=\"checkbox\" style=\"display: none;\" name=\"" + name + "\" checked=\"checked\" />");
                        }
                        $(e).parent().children("a.file-preview").text(data.filename);
                        $(e).parent().children("a.file-preview").attr("href", data.src + "?attachment=1");
                        $(e).parent().children("input.upload-input").val(data.path);
                    },
                    error: function(res) {
                        layer.close(show);
                        layer.alert(res);
                    }
                });
            });
            $("button.btn-upload-image").each(function(i, e) {
                upload.render({
                    elem: e,
                    url: $(e).data("upload-url"),
                    accept: $(e).data("accept"),
                    done: function(res) {
                        if (res.code !== 0) {
                            layer.alert(res.msg);
                        }
                        var data = res.data;
                        var name = $(e).attr("name");
                        name = "_" + name + "-changed";
                        if ($(e).parent().find("[name=\"" + name + "\"]").size() === 0) {
                            $(e).parent().append("<input type=\"checkbox\" style=\"display: none;\" name=\"" + name + "\" checked=\"checked\" />");
                        } else {
                            console.log("change flag");
                        }
                        $(e).parent().children("img.image-preview").attr("src", data.src);
                        $(e).parent().children("input.upload-input").val(data.path);
                    },
                    error: function(res) {
                        layer.alert(res);
                    }
                });
            });
        }
    };

    exports("dashboard", dashboard);
});