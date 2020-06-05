
layui.define(['layer', 'jquery'], function(exports) {
    var layer = layui.layer
    , $ = layui.$;

    var dashboard = {
        listen: function() {
            $('body').on('click', '[data-side-fold]', function() {
                var fold = $(this).data("side-fold");
                if (fold == "0") {
                    $(this).data("side-fold", "1");
                    $(this).removeClass("layui-icon-shrink-right");
                    $(this).addClass("layui-icon-spread-left");
                    $('body').addClass("layout-side-fold");
                } else {
                    $(this).data("side-fold", "0");
                    $(this).removeClass("layui-icon-spread-left");
                    $(this).addClass("layui-icon-shrink-right");
                    $('body').removeClass("layout-side-fold");
                }
            });
        }
    };

    exports('dashboard', dashboard);
});

layui.use(['layer', 'element', 'form', 'dashboard'], function(){
    var layer = layui.layer
    ,element = layui.element
    ,dashboard = layui.dashboard;
    dashboard.listen();
});
