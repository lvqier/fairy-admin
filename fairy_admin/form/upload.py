
import os

from flask_admin.form import FileUploadField as _FileUploadField, ImageUploadField as _ImageUploadField
from flask_admin.form import FileUploadInput as _FileUploadInput, ImageUploadInput as _ImageUploadInput
from flask_admin.helpers import get_url
from flask_admin.babel import gettext
from flask_admin._backwards import Markup
from wtforms import ValidationError
from wtforms.widgets import html_params
from werkzeug.datastructures import FileStorage

from PIL import Image


class FileUploadInput(_FileUploadInput):
    tag = 'upload'

    empty_template = (
        '<div class="upload-field">'
        ' <a class="file-preview"></a>'
        ' <button type="button" %(file)s>'
        '  <i class="layui-icon">&#xe67c;</i>'
        + '  <span>{}</span>'.format(gettext('Select File'))
        + ' </button>'
        ' <input class="upload-input" %(text)s />'
        ' <input type="checkbox" class="upload-delete" name="%(marker)s" title="Delete" />'
        '</div>'
    )

    data_template = (
        '<div class="upload-field">'
        ' <a class="file-preview" %(a)s>%(filename)s</a>'
        ' <button type="button" %(file)s>'
        '  <i class="layui-icon">&#xe67c;</i>'
        + '  <span>{}</span>'.format(gettext('Select File'))
        + ' </button>'
        ' <input class="upload-input" %(text)s />'
        ' <input type="checkbox" class="upload-delete" name="%(marker)s" title="Delete" />'
        '</div>'
    )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        kwargs.setdefault('class', 'layui-btn btn-upload-file')
        kwargs.setdefault('data-upload-url', get_url(field.upload_endpoint, field=field.name))
        kwargs.setdefault('data-accept', 'file')

        template = self.data_template if field.data else self.empty_template

        if field.errors:
            template = self.empty_template

        template_args = {
            'text': html_params(type='hidden',
                value=field.data,
                name=field.name),
            'file': html_params(type='file',
                value=field.data,
                **kwargs),
            'marker': '_%s-delete' % field.name
        }
        if field.data:
            template_args.update({
                'a': html_params(
                    href=get_url(field.endpoint, filename=field.data, attachment=1),
                    title=field.name),
                'filename': os.path.basename(field.data)
            })
        return Markup(template % template_args)


class FileUploadField(_FileUploadField):
    widget = FileUploadInput()

    def __init__(self, *args, endpoint='.static', upload_endpoint='.ajax_upload', **kwargs):
        super(FileUploadField, self).__init__(*args, **kwargs)
        self.endpoint = endpoint
        self.upload_endpoint = upload_endpoint

    def process_formdata(self, valuelist):
        data = None
        if valuelist:
            data = valuelist[0]

        if self._should_delete:
            self._delete_file(data)
            self.data = None
        else:
            self.data = data

    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)
        if field:
            if self._should_delete:
                self._delete_file(field)
                setattr(obj, name, None)
                return

        if self.data:
            filename = self.generate_name(obj, self.data)
            filename = self._save_file(self.data, filename)

            setattr(obj, name, filename)

    def _save_file(self, source_file, target_file):
        path = self._get_path(target_file)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission | 0o111)

        os.rename(self._get_path(source_file), self._get_path(target_file))
        return target_file


class ImageUploadInput(_ImageUploadInput):
    tag = 'upload-image'

    empty_template = (
        '<div class="upload-field upload-field-image">'
        ' <img class="image-preview" />'
        ' <button type="button" %(file)s>'
        '  <i class="layui-icon">&#xe67c;</i>'    
        + '  <span>{}</span>'.format(gettext('Select Image'))
        + ' </button>'
        ' <input class="upload-input" %(text)s />'
        ' <input type="checkbox" class="upload-delete" name="%(marker)s" title="Delete" disabled />'
        '</div>'
    )

    data_template = (
        '<div class="upload-field upload-field-image">'
        ' <img class="image-preview" %(image)s />'
        ' <button type="button" %(file)s>'
        '  <i class="layui-icon">&#xe67c;</i>'    
        + '  <span>{}</span>'.format(gettext('Select Image'))
        + ' </button>'
        ' <input class="upload-input" %(text)s />'
        ' <input type="checkbox" class="upload-delete" name="%(marker)s" title="Delete" />'
        '</div>'
    )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'layui-btn btn-upload-image')
        kwargs.setdefault('data-upload-url', get_url(field.upload_endpoint, field=field.name))
        kwargs.setdefault('data-accept', 'images')
        return super(ImageUploadInput, self).__call__(field, **kwargs)


class ImageUploadField(_ImageUploadField):
    widget = ImageUploadInput()

    def __init__(self, *args, endpoint='.static', upload_endpoint='.ajax_upload', **kwargs):
        super(ImageUploadField, self).__init__(*args, endpoint=endpoint, **kwargs)
        self.upload_endpoint = upload_endpoint

    def process_formdata(self, valuelist):
        data = None
        if valuelist:
            data = valuelist[0]

        if self._should_delete:
            self._delete_file(data)
            self.data = None
        else:
            self.data = data

    def pre_validate(self, form):
        super(ImageUploadField, self).pre_validate(form)
        if not self._should_delete and self.data:
            path = self._get_path(self.data)
            try:
                self.image = Image.open(path)
            except Exception as e:
                raise ValidationError('Invalid image: %s' % e)

    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)
        if field:
            if self._should_delete:
                self._delete_file(field)
                setattr(obj, name, None)
                return

        if self.data:
            filename = self.generate_name(obj, self.data)
            filename = self._save_file(self.data, filename)

            setattr(obj, name, filename)

    def _save_file(self, source_file, target_file):
        path = self._get_path(target_file)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission | 0o111)

        filename, format = self._get_save_format(target_file, self.image)

        if self.image and (self.image.format != format or self.max_size):
            if self.max_size:
                image = self._resize(self.image, self.max_size)
            else:
                image = self.image
            self._save_image(image, path, format)
        else:
            os.rename(self._get_path(source_file), self._get_path(target_file))

        self._save_thumbnail(source_file, target_file, format)
        
        return target_file
