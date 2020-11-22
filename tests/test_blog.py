import unittest
from base import http, test
from unittest.mock import patch
import os

current_file_folder = os.path.dirname(os.path.realpath(__file__))

from tests.test_base import token2user, SetUpTestblBlogServiceBase, id_user, id_session, random_uuid


@patch('base.token.token2user', token2user)
class Test(SetUpTestblBlogServiceBase):

    def test(self):
        self.api(None, 'GET', self.prefix() + '/about', expected_code=http.status.OK,
                 expected_result={"service": "blog"})


@patch('base.token.token2user', token2user)
class TestTag(SetUpTestblBlogServiceBase):

    def test(self):
        self.api(None, 'GET', self.prefix() + '/tags', expected_code=http.status.OK,
                 expected_length=0, expected_result=[])

        self.api("x", "POST", self.prefix() + "/tags", body={'tag': {
            "name": "test"
        }}, expected_code=http.status.CREATED)


@patch('base.token.token2user', token2user)
class TestPageTemplate(SetUpTestblBlogServiceBase):

    def test(self):
        self.api('x', 'GET', self.prefix() + '/templates', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'templates'})

        self.assertTrue(
            'total_items' in self.last_result['summary'] and self.last_result['summary']['total_items'] == 0)

        self.api('x', 'POST', self.prefix() + '/templates',
                 body={
                     'template': {'name': 'Template 1',
                                  'description': 'Tpl1Ddescription',
                                  'initial_nr_posts': 1}
                 }, expected_code=http.status.CREATED, expected_result_contain_keys={'id'})

        self.api('x', 'GET', self.prefix() + '/templates', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'templates'})

        self.assertTrue(
            'total_items' in self.last_result['summary'] and self.last_result['summary']['total_items'] == 1)

        self.show_last_result()


@patch('base.token.token2user', token2user)
class TestPage(SetUpTestblBlogServiceBase):

    def test(self):
        self.api('x', 'POST', self.prefix() + '/templates',
                 body={
                     'template': {'name': 'Template 1',
                                  'description': 'Tpl1Ddescription',
                                  'initial_nr_posts': 1}
                 }, expected_code=http.status.CREATED, expected_result_contain_keys={'id'})

        id_template = self.last_result['id']

        self.api('x', 'GET', self.prefix() + '/pages', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'pages'})

        self.assertTrue(
            'total_items' in self.last_result['summary'] and self.last_result['summary']['total_items'] == 0)

        self.api('x', 'POST', self.prefix() + '/pages',
                 body={
                     'page': {
                         'title': 'Test page',
                         'id_template': id_template
                     }

                 }, expected_code=http.status.CREATED, expected_result_contain_keys={'id'})

        self.api('x', 'GET', self.prefix() + '/pages', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'pages'})

        self.assertTrue(
            'total_items' in self.last_result['summary'] and self.last_result['summary']['total_items'] == 1)


@patch('base.token.token2user', token2user)
class TestPost(SetUpTestblBlogServiceBase):

    def test_add_simple_post(self):
        self.api('MOCKUPED', 'POST', '/api/blog/posts', body={'post': {
            'id_user': id_user,
            'title': 'ABC Post'
        }}, expected_code=http.status.CREATED, expected_result_contain_keys={'id'})

    def test_fetch_non_existing_post(self):
        self.api(None, 'GET', '/api/blog/posts/' + random_uuid, expected_code=http.status.NOT_FOUND)

    def test_fetch_simple_post(self):
        self.api("MOCKUPED", 'POST', '/api/blog/posts', body={'post': {
            'id_user': id_user,
            'title': 'ABC Post'
        }}, expected_code=http.status.CREATED)
        id_post = self.last_result['id']

        self.api(None, 'GET', '/api/blog/posts/' + id_post + "?fields=id", expected_code=http.status.OK, )
        self.assertTrue('id' in self.last_result)
        self.assertFalse('title' in self.last_result)

        self.api(None, 'GET', '/api/blog/posts/' + id_post + "?fields=title", expected_code=http.status.OK)
        self.assertFalse('id' in self.last_result)
        self.assertTrue('title' in self.last_result)

        self.api(None, 'GET', '/api/blog/posts/' + id_post + "?fields=id,title", expected_code=http.status.OK)
        self.assertTrue('id' in self.last_result)
        self.assertTrue('title' in self.last_result)

    def test_add_post_with_all_fields_and_fetch_it(self):
        r = self.api("MOCKUPED", 'POST', '/api/blog/posts', body={'post': {
            'id_user': id_user,
            'title': 'ABC Post',
            'subtitle': 'abc subtitle post',
            'intro': 'Short intro for post',
            'body': '<p>Long <b>text</b></p>'
        }}, expected_code=http.status.CREATED)
        r = self.api(None, 'GET', '/api/blog/posts/' + r['id'] + "?fields=slug,title,subtitle,body",
                     expected_code=http.status.OK)
        self.assertTrue('slug' in r and r['slug'] == 'abc-post')
        self.assertTrue('title' in r and r['title'] == 'ABC Post')
        self.assertTrue('subtitle' in r and r['subtitle'] == 'abc subtitle post')
        self.assertTrue('body' in r and r['body'] == '<p>Long <b>text</b></p>')

    def test(self):
        self.api(None, 'GET', self.prefix() + '/posts', expected_code=http.status.OK, expected_result={
            "summary": {"total_pages": 0, "total_items": 0, "page": 1, "per_page": 10, "next": None,
                        "previous": None}, "posts": []})

        self.api('x', 'POST', self.prefix() + '/posts',
                 body={
                     'post':
                         {
                             'title': 'Test Post',
                             'subtitle': 'post subtitle',
                             'body': '<b>Post</b> Text'
                         },
                     'tag_names': ['base3', 'test', 'post']
                 },
                 expected_code=http.status.CREATED)

        id_post = self.last_result['id']

        self.api(None, 'GET', self.prefix() + '/posts', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'posts'})

        self.assertTrue(self.last_result['summary']['total_items'] == 1)
        self.assertTrue(len(self.last_result['posts']) == 1)

        self.api(None, 'GET', self.prefix() + f'/posts/{id_post}', expected_code=http.status.OK)

        self.api('x', 'POST', self.prefix() + '/posts',
                 body={
                     'post':
                         {
                             'title': 'Another Test Post',
                             'subtitle': 'post 2 subtitle',
                             'body': '<b>Post2</b> Text'
                         },
                     'tag_names': ['base3', 'new']
                 },
                 expected_code=http.status.CREATED)

        self.api(None, 'GET', self.prefix() + '/posts?search=pera', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'posts'})
        self.assertTrue(len(self.last_result['posts']) == 0)

        self.api(None, 'GET', self.prefix() + '/posts?search=another', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'posts'})
        self.assertTrue(len(self.last_result['posts']) == 1)

        self.api(None, 'GET', self.prefix() + '/posts?search=test', expected_code=http.status.OK,
                 expected_result_contain_keys={'summary', 'posts'})
        self.assertTrue(len(self.last_result['posts']) == 2)

        self.show_last_result()


@patch('base.token.token2user', token2user)
class TestPhoto(SetUpTestblBlogServiceBase):

    def test(self):
        self.api('MOCKUPED', 'POST', '/api/blog/posts', body={'post': {
            'id_user': id_user,
            'title': 'ABC Post'
        }}, expected_code=http.status.CREATED, expected_result_contain_keys={'id'})

        id_post = self.last_result['id']

        photo = test.b64file(current_file_folder + '/sample_photos/digital-cube-logo.png')

        self.api('MOCKUPED', 'PUT', '/api/blog/photos/' + id_post,
                 {'data': photo, 'filename': 'digital-cube-logo.png'},
                 expected_code=http.status.CREATED,
                 expected_result_contain_keys={'uri'}
                 )

        uri = self.last_result['uri']

        self.api('MOCKUPED', 'GET', '/api/blog/photos/' + id_post,
                 expected_code=http.status.OK,
                 expected_result_contain_keys={'photos'})

        self.assertTrue(self.last_result['photos'][0]['uri'] == uri)



if __name__ == '__main__':
    unittest.main()
