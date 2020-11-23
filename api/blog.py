import base
from base import http
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import or_, desc
from tornado import gen
import os
from PIL import Image
import shutil
import base64
import hashlib

if base.config.conf['apptype'] == 'monolith':
    base.route.set('prefix', base.config.conf['services']['blog']['prefix'])
else:
    base.route.set('prefix', base.config.conf['prefix'])

import orm.models as models


@base.route('/about')
class AboutBlogServiceHandler(base.Base):

    @base.api()
    async def get(self):
        return {'service': 'blog'}


@base.route('/tags')
class Tag(base.Base):

    @base.api()
    async def get(self):
        return [[tag.name, tag.count] for tag in self.orm_session.query(models.Tag).all()]

    @base.auth()
    @base.api()
    async def post(self, tag: models.Tag):
        self.orm_session.add(tag)
        self.orm_session.commit()
        return {'id': tag.id}, http.status.CREATED


@base.route('/posts')
class PostHandler(base.Base):

    @base.auth()
    @base.api()
    async def post(self, post: models.Post, tag_names: list = []):
        self.orm_session.add(post)

        if tag_names:
            tag_names = list(set([t.lower().strip() for t in tag_names]))

            existing_tags = {tag.name: tag for tag in self.orm_session.query(models.Tag).
                filter(models.Tag.name.in_(tag_names)).all()}

            for tag_name in tag_names:
                if tag_name in existing_tags:
                    existing_tags[tag_name].count += 1
                    self.orm_session.add(models.Post2Tag(post=post, tag=existing_tags[tag_name]))
                else:
                    new_tag = models.Tag(name=tag_name, count=1)
                    self.orm_session.add(new_tag)
                    self.orm_session.add(models.Post2Tag(post=post, tag=new_tag))

        if post.slug:
            # this will check slug, and throw exception if slug is occupied
            post.slugify(slug=post.slug, commit=False)
        else:
            # this will automatically generate slug in several attampts, or throw exception if slug is occupied
            post.slugify(slug=None, commit=False)

        post.index4search(commit=False)

        self.orm_session.commit()
        return {'id': post.id}, http.status.CREATED

    @base.api()
    async def get(self, page: int = 1, per_page: int = 10, search: str = None, id_tags: list = None,
                  fields: str = 'id,title'):

        filters = []

        query = self.orm_session.query(models.Post)

        uri_pfx = []

        if search:
            uri_pfx.append(f'search={search}')
            query = query.join(models.PostSearch)
            search = search.lower().strip()
            filters.append(models.PostSearch.search.like(f"%{search}%"))

        if id_tags:
            uri_pfx.append(f'id_tags={id_tags}')
            query = query.join(models.Post2Tag)
            filters.append(models.Post2Tag.id_tag.in_(id_tags))

        uri_pfx = '&'.join(uri_pfx)
        if uri_pfx:
            uri_pfx = f'?{uri_pfx}'

        query = query.filter(*filters)

        query, summary = base.paginate(query, f'/api/blog/posts{uri_pfx}', page, per_page)

        fields = fields.split(',') if fields else None

        return {'summary': summary,
                'posts': [p.serialize(fields) for p in query.all()]}


@base.route('/posts/:id_post')
class SinglePostHandler(base.Base):

    @base.api()
    async def get(self, post: models.Post.id, fields: str = 'id,title,subtitle,body'):
        if not post:
            raise http.HttpErrorNotFound(id_message="POST_NOT_FOUND",
                                         message="Post not found")

        return post.serialize(fields.split(',') if fields else None)


@base.route('/templates')
class TemplateHandler(base.Base):

    @base.auth()
    @base.api()
    async def post(self, template: models.PageTemplate):
        self.orm_session.add(template)
        self.orm_session.commit()
        return {'id': template.id}, http.status.CREATED

    @base.auth()
    @base.api()
    async def get(self, page: int = 1, per_page: int = 10, search: str = None, fields: str = 'id,name'):

        filters = []
        query = self.orm_session.query(models.PageTemplate)

        uri_pfx = []

        if search:
            uri_pfx.append(f'search={search}')
            search = search.lower().strip()
            filters.append(or_(
                models.PageTemplate.name.like(f"%{search}%"),
                models.PageTemplate.description.like(f"%{search}%")))

        uri_pfx = '&'.join(uri_pfx)
        if uri_pfx:
            uri_pfx = f'?{uri_pfx}'

        query = query.filter(*filters)

        query, summary = base.paginate(query, f'/api/blog/templates{uri_pfx}', page, per_page)

        fields = fields.split(',') if fields else None

        return {'summary': summary,
                'templates': [t.serialize(fields) for t in query.all()]}


@base.route('/pages')
class PageHandler(base.Base):

    @base.auth()
    @base.api()
    async def post(self, page: models.BlogPage):
        self.orm_session.add(page)
        self.orm_session.commit()
        return {'id': page.id}, http.status.CREATED

    @base.auth()
    @base.api()
    async def get(self, page: int = 1, per_page: int = 10, search: str = None, fields: str = 'id,title,id_template'):

        filters = []
        query = self.orm_session.query(models.BlogPage)

        uri_pfx = []

        if search:
            uri_pfx.append(f'search={search}')
            search = search.lower().strip()
            filters.append(or_(
                models.BlogPage.name.like(f"%{search}%"),
                models.BlogPage.description.like(f"%{search}%")))

        uri_pfx = '&'.join(uri_pfx)
        if uri_pfx:
            uri_pfx = f'?{uri_pfx}'

        query = query.filter(*filters)

        query, summary = base.paginate(query, f'/api/blog/pages{uri_pfx}', page, per_page)

        fields = fields.split(',') if fields else None

        return {'summary': summary,
                'pages': [p.serialize(fields) for p in query.all()]}



@base.route(URI="/editor/photos/:id_post")
class EditorPhotoServiceHandler(base.Base):
    executor = ThreadPoolExecutor(max_workers=32)

    @base.auth()
    @base.api()
    # @gen.coroutine
    async def post(self, **kwargs):

        storage = base.config.conf['storage']
        static = base.config.conf['static']

        if storage[-1] == '/':
            storage = storage[:-1]
        if static[-1] == '/':
            static = static[:-1]

        if self.request.files and 'file' in self.request.files:
            if len(self.request.files['file']) > 0:
                fname = self.request.files['file'][0]['filename']
                body = self.request.files['file'][0]['body']

                with open(storage + '/' + fname, 'wb') as f:
                    f.write(body)

                # res = yield self.save_photo()

                return {'location': static + fname}

        raise http.HttpInternalServerError


@base.route(URI="/photos/:id_post")
class PostPhotoServiceHandler(base.Base):
    executor = ThreadPoolExecutor(max_workers=32)

    @base.api()
    async def get(self, id_post: str):
        static = base.config.conf['static']
        if static[-1] == '/':
            static = static[:-1]

        return {
            'photos': [{'id': p.id, 'format': p.format,
                        'filename': p.filename,
                        'uri': static + '/' + p.id + '.' + p.format} for p in
                       self.orm_session.query(models.Photo).filter(models.Photo.id_post == id_post).order_by(
                           desc(models.Photo.created)).all()]}

    @run_on_executor
    def save_photo(self, id_post: str, data: str, filename: str = None, group: str = None):

        from orm.orm import session
        sess = session()

        try:

            edata = data.encode()
            try:
                if b',' in edata:
                    edata = edata.split(b',')[-1]
            except Exception as e:
                print(e)

            binary = base64.decodebytes(edata)

            photo = models.Photo(id_user=self.id_user,
                                 id_post=id_post,
                                 filename=filename)

            storage = base.config.conf['storage']
            static = base.config.conf['static']

            if static[-1] == '/':
                static = static[:-1]

            if storage[-1] == '/':
                storage = storage[:-1]

            temporary_local_filename = f"{storage}/{photo.id}.saved"

            try:
                with open(temporary_local_filename, 'wb') as f:
                    f.write(binary)
                    photo.filesize = len(binary)
            except:
                raise http.HttpInternalServerError('Error saving photo')

            try:
                im = Image.open(temporary_local_filename)
                photo.width = im.size[0]
                photo.height = im.size[1]
                photo.format = str(im.format).lower()
                im.close()
            except:
                # return {'message': 'Error decoding input data'}, http.status.BAD_REQUEST
                raise http.HttpInvalidParam('Error decoding input data')

            local_filename = f"{storage}/{photo.id}.{photo.format}"

            try:
                os.rename(temporary_local_filename, local_filename)

            except:
                raise http.HttpInternalServerError('Error saving photo with format')

            try:
                with open(local_filename, "rb") as f:
                    sha256hash = hashlib.sha256(f.read()).hexdigest()
            except:
                raise http.HttpInternalServerError('error calculating hash')

            photo.hash = sha256hash

            photo.group = group

            sess.add(photo)
            sess.commit()

            return {'uri': static + '/' + local_filename.split('/')[-1]}, http.status.CREATED

        except BaseException as e:
            sess.rollback()
            raise http.HttpInternalServerError('Error saving photo info into database')

    @base.auth()
    @base.api()
    @gen.coroutine
    def put(self, id_post: str, data: str, filename: str = None, group: str = None):

        return (yield self.save_photo(id_post, data, filename, group))
