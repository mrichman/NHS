#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wordpress Client
"""

from ConfigParser import SafeConfigParser, Error
import logging
import oursql
import os
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods.users import GetUsers


class WordPressClient(object):
    def get_blog_subscribers(self):
        """ Gets WordPress Blog Subscribers """
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        try:
            url = config.get("wordpress", "url")
            username = config.get("wordpress", "username")
            password = config.get("wordpress", "password")
        except Error as error:
            msg = "Config section [wordpress] bad or missing: %s" % \
                  error.message
            logging.error(msg)
            raise Exception(msg)

        subs = []

        wp = Client(url, username, password)
        users = wp.call(GetUsers())
        logging.info("Found %d users." % len(users))
        for u in users:
            logging.debug("User: %s" % u.email)
            logging.debug("Roles: %s" % u.roles)
            if 'subscriber' in u.roles:
                subs.append((u.email, u.first_name))
        return subs

    def get_blog_unubscribers(self):
        pass


class WordPressDBClient(object):
    def __init__(self):
        config = SafeConfigParser()
        try:
            config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        except Error:
            msg = "config.ini file bad or missing"
            logging.error(msg)
            raise Exception(msg)
        try:
            self.username = config.get("wordpressdb", "user")
            self.password = config.get("wordpressdb", "password")
            self.host = config.get("wordpressdb", "host")
            self.db = config.get("wordpressdb", "db")
        except Error:
            msg = "Config section [wordpressdb] bad or missing"
            logging.error(msg)
            raise Exception(msg)

    def get_blog_subscribers(self):
        """ Gets WordPress Blog Subscribers """
        logging.info("Getting blog subscribers.")
        conn = oursql.connect(host=self.host, user=self.username,
                              passwd=self.password, db=self.db)
        curs = conn.cursor(oursql.DictCursor)

        sql = (
            "SELECT users.user_email, users.display_name "
            "FROM admin_wpdb.wp_usermeta meta "
            "INNER JOIN admin_wpdb.wp_users users ON "
            "   (users.ID = meta.user_id) "
            "WHERE meta.meta_key = 'wp_capabilities' "
            "AND meta.meta_value LIKE '%subscriber%' "
            "ORDER BY users.ID")

        logging.debug(sql)

        try:
            curs.execute(sql)
        except Error as error:
            logging.error(error.message)
            raise Exception(error.message)

        users = []

        rows = curs.fetchall()
        for row in rows:
            user = (row['user_email'], row['display_name'])
            logging.debug(user)
            users.append(user)

        logging.info("Found %d blog subscribers." % len(users))
        return users

    def get_blog_unubscribers(self):
        pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    # console handler with specified log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(console_handler)
    wp = WordPressClient()
    wp.get_blog_subscribers()
