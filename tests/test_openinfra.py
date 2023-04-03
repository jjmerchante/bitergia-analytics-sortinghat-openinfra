# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import datetime
import json
import os

import httpretty
from dateutil.tz import tzutc
from django.test import TestCase
from django.contrib.auth import get_user_model

from sortinghat.core.context import SortingHatContext
from sortinghat.core.importer.backends.openinfra import OpenInfraIDImporter, OpenInfraIDParser

OPENINFRA_URL = 'https://openstackid-resources.openstack.org'
OPENINFRA_MEMBERS_URL = OPENINFRA_URL + '/api/public/v1/members'


def read_file(filename, mode='r'):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        content = f.read()
    return content


def setup_mock_server():
    """Configure a Mock server"""

    def request_callback(request, uri, headers):
        page = int(request.querystring.get('page', [1])[0])
        body = bodies[page - 1]
        requests.append(httpretty.last_request())
        return [200, headers, body]

    requests = []
    bodies = [read_file('data/openinfra_page_1.json'),
              read_file('data/openinfra_page_2.json')]

    httpretty.register_uri(httpretty.GET,
                           OPENINFRA_MEMBERS_URL,
                           responses=[
                               httpretty.Response(body=request_callback)
                               for _ in bodies
                           ])
    return requests, bodies


class TestOpenInfraImporter(TestCase):
    """OpenInfraIDImporter tests"""

    def setUp(self):
        """Initialize variables"""

        self.user = get_user_model().objects.create(username='test')
        self.ctx = SortingHatContext(self.user)

    def test_initialization(self):
        """Test whether attributes are initialized"""

        url = "https://test-url.com/"

        importer = OpenInfraIDImporter(ctx=self.ctx,
                                       url=url)

        self.assertEqual(importer.url, url)
        self.assertEqual(importer.ctx, self.ctx)
        self.assertEqual(importer.NAME, "OpenInfraID")
        self.assertIsNone(importer.from_date)

        # Check from_date is parsed correctly
        importer = OpenInfraIDImporter(ctx=self.ctx,
                                       url=url,
                                       from_date="2023-12-01")
        self.assertEqual(importer.from_date, datetime.datetime(year=2023,
                                                               month=12,
                                                               day=1,
                                                               tzinfo=tzutc()))

    def test_backend_name(self):
        """Test whether the NAME of the backend is right"""

        self.assertEqual(OpenInfraIDImporter.NAME, "OpenInfraID")


class TestOpenInfraParser(TestCase):
    """OpenInfraParser tests"""

    def test_initialization(self):
        """Test whether attributes are initialized"""

        parser = OpenInfraIDParser(OPENINFRA_URL)
        self.assertEqual(parser.url, OPENINFRA_URL)
        self.assertEqual(parser.source, 'openinfra')

    @httpretty.activate
    def test_fetch_items(self):
        """Test whether fetch items returns paginated items"""

        # Set up a mock HTTP server
        requests, bodies = setup_mock_server()

        # Run fetch items
        raw_items = OpenInfraIDParser.fetch_items(OPENINFRA_MEMBERS_URL)
        items = [item for item in raw_items]
        self.assertEqual(len(items), 2)
        self.assertDictEqual(items[0], json.loads(bodies[0]))
        self.assertDictEqual(items[1], json.loads(bodies[1]))

        # Check requests
        expected_qs = [
            {},
            {'page': ['2']}
        ]
        self.assertEqual(len(requests), 2)
        for i, req in enumerate(requests):
            self.assertDictEqual(req.querystring, expected_qs[i])
            self.assertEqual(req.url.split('?')[0], OPENINFRA_MEMBERS_URL)

    @httpretty.activate
    def test_fetch_items_with_payload(self):
        """Test whether fetch items from date returns paginated items"""

        # Set up a mock HTTP server
        requests, bodies = setup_mock_server()

        # Run fetch items
        payload = {OpenInfraIDParser.PSORT: '-last_edited'}
        raw_items = OpenInfraIDParser.fetch_items(OPENINFRA_MEMBERS_URL, payload=payload)

        items = [item for item in raw_items]
        self.assertEqual(len(items), 2)
        self.assertDictEqual(items[0], json.loads(bodies[0]))
        self.assertDictEqual(items[1], json.loads(bodies[1]))

        # Check requests
        expected_qs = [
            {'sort': ['-last_edited']},
            {'sort': ['-last_edited'], 'page': ['2']}
        ]
        self.assertEqual(len(requests), 2)
        for i, req in enumerate(requests):
            self.assertDictEqual(req.querystring, expected_qs[i])
            self.assertEqual(req.url.split('?')[0], OPENINFRA_MEMBERS_URL)

    @httpretty.activate
    def test_fetch_members(self):
        """Test whether fetch_members returns members"""

        # Set up a mock HTTP server
        requests, bodies = setup_mock_server()

        # Run fetch members
        parser = OpenInfraIDParser(OPENINFRA_URL)
        members = [member for member in parser.fetch_members()]

        self.assertEqual(len(members), 15)

        # Check requests
        expected_qs = [
            {'page': ['1'], 'per_page': ['100'], 'sort': ['-last_edited']},
            {'page': ['2'], 'per_page': ['100'], 'sort': ['-last_edited']}
        ]
        self.assertEqual(len(requests), 2)
        for i, req in enumerate(requests):
            self.assertDictEqual(req.querystring, expected_qs[i])
            self.assertEqual(req.url.split('?')[0], OPENINFRA_MEMBERS_URL)

    @httpretty.activate
    def test_fetch_members_from_date(self):
        """Test whether fetch_members returns members from a given date"""

        # Set up a mock HTTP server
        requests, bodies = setup_mock_server()

        # Run fetch members
        parser = OpenInfraIDParser(OPENINFRA_URL)
        from_date = datetime.datetime(year=2000, month=1, day=1, tzinfo=tzutc())
        members = [member for member in parser.fetch_members(from_date)]

        self.assertEqual(len(members), 15)

        # Check requests
        expected_qs = [
            {
                'page': ['1'],
                'per_page': ['100'],
                'sort': ['-last_edited'],
                'filter': ['last_edited>946684800']
            },
            {
                'page': ['2'],
                'per_page': ['100'],
                'sort': ['-last_edited'],
                'filter': ['last_edited>946684800']
            }
        ]
        self.assertEqual(len(requests), 2)
        for i, req in enumerate(requests):
            self.assertDictEqual(req.querystring, expected_qs[i])
            self.assertEqual(req.url.split('?')[0], OPENINFRA_MEMBERS_URL)

    @httpretty.activate
    def test_fetch_individuals(self):
        """Test fetch_individuals returns individuals"""

        # Set up a mock HTTP server
        requests, bodies = setup_mock_server()

        # Run fetch individuals
        parser = OpenInfraIDParser(OPENINFRA_URL)
        individuals = [indiv for indiv in parser.individuals()]

        # Not all individuals have valid information (name or GitHub username)
        self.assertEqual(len(individuals), 5)

        indiv = individuals[0]
        self.assertEqual(indiv.uuid, 136832)
        self.assertEqual(indiv.profile.name, "name surname")
        self.assertEqual(indiv.profile.is_bot, False)
        self.assertEqual(indiv.identities[0].source, "openinfra")
        self.assertEqual(indiv.identities[0].name, "name surname")
        self.assertEqual(indiv.identities[0].username, "136832")
        self.assertEqual(indiv.identities[1].source, "github")
        self.assertEqual(indiv.identities[1].name, "name surname")
        self.assertEqual(indiv.identities[1].username, "random-gh-user")

        indiv = individuals[1]
        self.assertEqual(indiv.uuid, 136853)
        self.assertEqual(indiv.profile.name, None)
        self.assertEqual(indiv.profile.is_bot, False)
        self.assertEqual(indiv.identities[0].source, "github")
        self.assertEqual(indiv.identities[0].name, "")
        self.assertEqual(indiv.identities[0].username, "random-gh-user-2")

        indiv = individuals[2]
        self.assertEqual(indiv.uuid, 125525)
        self.assertEqual(indiv.profile.name, "name_3 last_name_3")
        self.assertEqual(indiv.profile.gender, None)
        self.assertEqual(indiv.identities[0].source, "openinfra")
        self.assertEqual(indiv.identities[0].name, "name_3 last_name_3")
        self.assertEqual(indiv.identities[0].username, "125525")
        self.assertEqual(indiv.enrollments[0].start,
                         datetime.datetime(2020, 9, 1, tzinfo=tzutc()))
        self.assertEqual(indiv.enrollments[0].end, None)
        self.assertEqual(indiv.enrollments[0].organization.name, "Technology Org")

        # Check requests
        expected_qs = [
            {'page': ['1'], 'per_page': ['100'], 'sort': ['-last_edited']},
            {'page': ['2'], 'per_page': ['100'], 'sort': ['-last_edited']}
        ]
        self.assertEqual(len(requests), 2)
        for i, req in enumerate(requests):
            self.assertDictEqual(req.querystring, expected_qs[i])
            self.assertEqual(req.url.split('?')[0], OPENINFRA_MEMBERS_URL)
