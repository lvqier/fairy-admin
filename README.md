# Fairy Admin

This is an shell package which add [Layui](https://www.layui.com/) base template to Flask Admin


## Install

```
pip install git+https://github.com/lvqier/fairy-admin.git
```

## Usage

To use Layui, replace flask_admin.Admin with fairy_admin.FairyAdmin and use 'layui' for template_mode

For example:
```
> from fairy_admin import FairyAdmin
> admin = FairyAdmin(name='demo', template_mode='layui')
> # use admin as usual

```
