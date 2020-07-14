# Fairy Admin

This is a shell package which add [Layui](https://www.layui.com/) based template to [Flask Admin](https://github.com/flask-admin/flask-admin)

Only **[SQLAlchemy](http://www.sqlalchemy.org/)** backend supported.


## Install

```
pip install git+https://github.com/lvqier/fairy-admin.git
```

## Usage

To use Layui, replace flask_admin.Admin with fairy_admin.FairyAdmin and pass 'layui' for template_mode

For example:
```
> from fairy_admin import FairyAdmin
> from fairy_admin.contrib.sqla import ModelView
> # from somewhere import db, SampleModel
>
> admin = FairyAdmin(template_mode='layui')
> # use admin as usual
>
> class SampleModelView(ModelView):
>     pass
>
> admin.add_view(SampleModelView(SampleModel, db.session))

```


## Migrate from Flask Admin

|Flask Admin|Fairy Admin|
|-----------|-----------|
|flask_admin.Admin|fairy_admin.FairyAdmin|
|flask_admin.BaseModelView|fairy_admin.BaseModelView|
|flask_admin.contrib.sqla.ModelView|fairy_admin.contrib.sqla.ModelView|
|flask_admin.form.FileUploadField|fairy_admin.form.FileUploadField|
|flask_admin.form.ImageUploadField|fairy_admin.form.ImageUploadField|
