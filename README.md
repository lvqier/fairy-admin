# Fairy Admin

This is a shell package which add [Layui](https://www.layui.com/) based template to [Flask Admin](https://github.com/flask-admin/flask-admin)


## Install

```
pip install git+https://github.com/lvqier/fairy-admin.git
```

## Usage

To use Layui, replace flask_admin.Admin with fairy_admin.FairyAdmin and pass 'layui' for template_mode

For example:
```
> from fairy_admin import FairyAdmin
> admin = FairyAdmin(template_mode='layui')
> # use admin as usual

```
